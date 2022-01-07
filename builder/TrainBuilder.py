import base64
import os
import tarfile

from typing import List
import docker
import redis
import requests
from io import BytesIO
from docker.models.containers import Container
import json
from tarfile import TarInfo, TarFile
import time
from dotenv import load_dotenv, find_dotenv
import logging
from loguru import logger
from hvac import Client
from requests import HTTPError

from train_lib.clients import PHTClient

from builder.messages import QueueMessage, BuilderCommands, BuildMessage
from builder.tb_store import BuildStatus, BuilderRedisStore

LOGGER = logging.getLogger(__name__)


class TrainBuilder:
    vault_url: str
    vault_token: str
    registry_url: str
    registry_domain: str
    harbor_user: str
    harbor_password: str
    redis_host: str

    docker_client: docker.DockerClient
    vault_client: Client = None
    redis_client: redis.Redis = None
    redis_store: BuilderRedisStore = None

    def __init__(self):
        load_dotenv(find_dotenv())
        # Run setup
        self._setup()

        assert self.vault_url and self.vault_token and self.registry_url

    def process_message(self, msg: dict):

        message = QueueMessage(**msg)

        logger.info(f"Processing message: {message}")
        train_id = message.data.get("trainId")
        if not train_id:
            logger.error("Train id not found in message")
            status = BuildStatus.NOT_FOUND
            # todo return error message

        if message.type == BuilderCommands.START:
            build_message = BuildMessage(**msg)
            # todo start build
        elif message.type == BuilderCommands.STOP:
            # todo stop build
            pass

        elif message.type == BuilderCommands.STATUS:

            if self.redis_store.train_exists(train_id):
                status = self.redis_store.get_build_status(train_id=train_id)
            else:
                status = BuildStatus.NOT_FOUND

        # todo make response

    def _setup(self):
        """
        Ensure that the docker client has access to the harbor repository

        :return:
        """
        # Connect to redis either in docker-compose container or on localhost
        logger.info("Initializing docker client and logging into registry")
        self.docker_client = docker.client.from_env()
        self.registry_url = os.getenv("HARBOR_URL")
        self.registry_domain = self.registry_url.split("//")[1]
        if not self.registry_url:
            raise ValueError("HARBOR_URL not set")

        self.harbor_user = os.getenv("HARBOR_USER")
        self.harbor_password = os.getenv("HARBOR_PW")

        if not self.harbor_user and self.harbor_password:
            raise ValueError("Harbor user and password must be set in environment variables -> HARBOR_USER + HARBOR_PW")

        login_result = self.docker_client.login(username=self.harbor_user, password=self.harbor_password,
                                                registry=self.registry_url)
        logger.info(f"Login result -- {login_result['Status']}")

        logger.info("Initializing vault client")

        self.vault_url = os.getenv("VAULT_URL")
        self.vault_token = os.getenv("VAULT_TOKEN")

        if not self.vault_url and self.vault_token:
            raise ValueError("Vault url and token must be set in environment variables -> VAULT_URL + VAULT_TOKEN")
        self.vault_client = Client(
            url=self.vault_url,
            token=self.vault_token
        )

        logger.info("Vault client initialized")

        logger.info("Requesting service token")
        self._get_service_token()
        logger.info("Service token obtained")

        self.api_url = os.getenv("UI_TRAIN_API")

        logger.info("Connecting to redis")
        self.redis_host = os.getenv("REDIS_HOST")
        self.redis = redis.Redis(host=self.redis_host, decode_responses=True)
        logger.info("Redis connection established")
        logger.info("Validating setup")
        self._validate_setup()
        logger.info("Setup complete")

    def build(self, build_message: BuildMessage):

        logger.info(f"Ensuring master image - {build_message.master_image} is available...")
        master_image_repo = self._make_master_image_tag(build_message.master_image)
        self.docker_client.images.pull(master_image_repo, tag="latest")

        image, logs = self._build_image(build_message)
        logger.info(f"Image built - {image.id}")
        logger.debug(f"Logs - {logs}")


    def generate_config(self, build_message: BuildMessage):
        pass


    def _make_master_image_tag(self, master_image: str):
        return f"{self.registry_domain}/{master_image}"

    def _build_image(self, build_message: BuildMessage):

        logger.info(f"Building base image for Train - {build_message.train_id}")
        docker_file_obj = self._make_dockerfile(
            master_image=build_message.master_image,
            command_args=build_message.entrypoint_args,
            entrypoint_file=build_message.entrypoint_path,
            command=build_message.entrypoint_executable,
        )
        image, logs = self.docker_client.images.build(fileobj=docker_file_obj)
        return image, logs

    def build_train(self, build_data: dict, meta_data: dict):
        """
        Builds the train based two dictionaries containing build and metadata

        :param build_data:
        :param meta_data:
        :return:
        """

        # pull master image
        registry = os.getenv("HARBOR_URL").split("//")[-1]
        master_image = f"{registry}/master/{build_data['masterImage']}"
        logger.info(f"Train: {build_data['trainId']} -- Pulling master image {master_image}...")
        self.docker_client.images.pull(master_image, tag="latest")

        # try:
        docker_file_obj = self._make_dockerfile(
            master_image=build_data["masterImage"],
            command=build_data["entrypointCommand"],
            command_args=build_data["entrypointCommandArguments"],
            entrypoint_file=build_data["entrypointPath"])

        logger.info(f"Train: {build_data['trainId']} -- Building image")
        # Build the image based on the specifications passed in the message
        image, logs = self.docker_client.images.build(fileobj=docker_file_obj)
        # Start a temporary container
        logger.info(f"Train: {build_data['trainId']} -- Starting temporary container")
        container = self.docker_client.containers.create(image.id)
        # Generate the train config file and query

        logger.info(f"Train: {build_data['trainId']} -- Generating query archive")
        query_archive = None

        if build_data["query"]:
            query_archive = self._make_query(build_data["query"])
        if query_archive:
            immutable_files = build_data["files"] + ["./query.json"]
            build_data["files"] = immutable_files
        config_archive = self._make_train_config(build_data, meta_data)
        # Add files from API to container
        self._add_train_files(container, build_data["trainId"], config_archive, query_archive)
        self._tag_and_push_images(container, build_data["trainId"])
        # Post route to vault to start processing
        logger.info("build data: {} ", build_data)
        print(build_data["stations"])
        self.pht_client.post_route_to_vault(build_data["trainId"], build_data["stations"])
        logger.info(f"Train: {build_data['trainId']} -- Build finished")

        self.set_redis_status(build_data["trainId"], BuildStatus.FINISHED)
        return 0, "train successfully built"

    def get_train_status(self, train_id: str):

        status = self._get_redis_status(train_id)
        logger.info(f"Getting status for train: {train_id} --> {status}")
        message = {
            "type": status,
            "data": {
                "trainId": train_id
            }
        }
        return message

    def set_redis_status(self, train_id: str, state: BuildStatus):
        """
        Set the status of the train defined by its id to one of the enum values of BuildStatus

        :param train_id: id of the train
        :param state: enum identifier of the build status
        :return:
        """
        self.redis.set(f"{train_id}-tb-status", state.value)

    def _validate_setup(self):
        fields = vars(self)

        for key in fields:
            if not fields[key]:
                raise ValueError(f"Instance variable {key} could not be initialized.")

    def _get_redis_status(self, train_id: str) -> str:
        train_status = self.redis.get(f"{train_id}-tb-status")
        if train_status:
            return train_status
        else:
            return BuildStatus.NOT_FOUND.value

    def _add_train_files(self, container: Container, train_id, config_archive, query_archive=None):
        """
        Get a tar archive containing uploaded train files from the central service and place them in the
        specified container. The previously generated config and query files are also added to the container

        :param container: docker Container object to which to add the files
        :param train_id: id of the train for querying the files from the central server
        :param config_archive: tar archive containing a json file
        :param query_archive: tar archive containing the json definition of a fhir query
        :return:
        """

        logger.info(f"Train: {train_id} -- Adding files to container")
        # Get the train files from pht API
        train_archive = self.pht_client.get_train_files_archive(train_id=train_id, token=self.service_key,
                                                                client_id=self.client_id)
        container.put_archive("/opt/pht_train", train_archive)
        container.wait()
        container.put_archive("/opt", config_archive)
        if query_archive:
            container.put_archive("/opt/pht_train", query_archive)

    def get_train_files(self, train_id: str) -> BytesIO:

        logger.info(f"Train: {train_id} -- Getting files from central API")
        try:
            train_archive = self._get_tar_archive_from_api(train_id)
        except HTTPError:
            logger.error(f"Error getting train files from central API")
            logger.info(f"Attempting to refresh service credentials")
            self._get_service_token()
            train_archive = self._get_tar_archive_from_api(train_id)

        return train_archive

    def _get_tar_archive_from_api(self, train_id: str) -> BytesIO:
        """
        Read a stream of tar data from the given endpoint and return an in memory BytesIO object containing the data

        :param endpoint: address relative to this instances api address
        :param params: dictionary containing additional parameters to be passed to the request
        :param external_endpoint: boolean parameter controlling whether the URL where the request is sent should built using
        the combination of api + endpoint or if the connection should be attempted on the raw endpoint string

        :return:
        """
        url = f"{self.api_url}{train_id}/files/download"
        headers = self._create_api_headers(api_token=self.service_key, client_id=self.client_id)
        with requests.get(url, headers=headers, stream=True) as r:
            r.raise_for_status()
            file_obj = BytesIO()
            for chunk in r.iter_content():
                file_obj.write(chunk)
            file_obj.seek(0)

        return file_obj

    @staticmethod
    def _create_api_headers(api_token: str, client_id: str = "TRAIN_BUILDER") -> dict:
        auth_string = f"{client_id}:{api_token}"
        auth_string = base64.b64encode(auth_string.encode("utf-8")).decode()
        headers = {"Authorization": f"Basic {auth_string}"}
        return headers

    def _make_train_config(self, build_data: dict, meta_data: dict):
        """
        Generate a tar archive containing a json file train_config.json in which the relevant security values for the
        train will be stored

        :param build_data: dictionary containing build data sent from the central ui
        :param meta_data:
        :return:
        """

        logger.info(f"Train: {build_data['trainId']} -- Generating train config")

        user_public_key = self.pht_client.get_user_public_key(build_data["userId"])

        station_public_keys = self.pht_client.get_multiple_station_pks(build_data["stations"])
        registry = os.getenv("HARBOR_URL").split("//")[-1]
        master_image = f"{registry}/master/{build_data['masterImage']}"

        config = {
            "master_image": master_image,
            "user_id": build_data["userId"],
            "train_id": build_data["trainId"],
            "session_id": build_data["sessionId"],
            "rsa_user_public_key": user_public_key,
            "encrypted_key": None,
            "rsa_public_keys": station_public_keys,
            "e_h": build_data["hash"],
            "e_h_sig": build_data.get("hashSigned", None),
            "e_d": None,
            "e_d_sig": None,
            "digital_signature": None,
            "proposal_id": build_data["proposalId"],
            "user_he_key": build_data.get("user_he_key", None),
            "immutable_file_list": build_data["files"]
        }

        config_archive = BytesIO()
        tar = tarfile.open(fileobj=config_archive, mode="w")
        # transform  to bytesIo containing binary json data
        config = BytesIO(json.dumps(config, indent=2).encode("utf-8"))

        # Create TarInfo Object based on the data
        config_file = TarInfo(name="train_config.json")
        config_file.size = config.getbuffer().nbytes
        config_file.mtime = time.time()
        # add config data and reset the archive
        tar.addfile(config_file, config)
        tar.close()
        config_archive.seek(0)

        return config_archive

    @staticmethod
    def _make_query(query) -> BytesIO:
        """
        Create a query archive from the passed query object from the ui

        :param query:
        :return:
        """
        query = BytesIO(query.encode("utf-8"))
        query_archive = BytesIO()
        tar = tarfile.open(fileobj=query_archive, mode="w")
        query_file = TarInfo(name="query.json")
        query_file.size = query.getbuffer().nbytes
        query_file.mtime = time.time()
        tar.addfile(query_file, query)
        tar.close()
        query_archive.seek(0)

        return query_archive

    def _tag_and_push_images(self, container: Container, train_id: str):
        """
        Gets a previously created container for distribution by committing the passed container object to a base and a
        latest image identified by the train_id and pushes these images to the pht_incoming repository in harbor.

        :param container:
        :param train_id:
        :return:
        """

        registry = os.getenv("HARBOR_URL").split("//")[-1]
        repo = f"{registry}/pht_incoming/{train_id}"
        logger.info(f"Train: {train_id} -- Committing train images, repo: {repo}")
        container.commit(repo, tag="latest")
        container.commit(repo, tag="base")
        logger.info(f"Train: {train_id} -- Pushing images")
        push_latest = self.docker_client.images.push(repo, tag="latest")
        push_base = self.docker_client.images.push(repo, tag="base")
        # remove images after building
        logger.info(f"Train: {train_id} -- Removing train artifacts")
        self.docker_client.images.remove(repo + ":base", noprune=False, force=True)
        self.docker_client.images.remove(repo + ":latest", noprune=False, force=True)

    def _make_dockerfile(self, master_image: str, command: str, entrypoint_file: str, command_args: List[str] = None):

        train_dir = "/opt/pht_train"
        results_dir = "/opt/pht_results"

        if command_args:
            docker_command_args = [f'"{arg}"' for arg in command_args]
            docker_command_args = ", ".join(docker_command_args) + ", "
        else:
            docker_command_args = ""

        if entrypoint_file[:2] == "./":
            entrypoint_file = entrypoint_file[2:]

        docker_from = f"FROM {self.registry_domain}/master/{master_image}\n"
        directory_setup = f"RUN mkdir {train_dir} && mkdir {results_dir} && chmod -R +x {train_dir} \n"
        docker_command = f'CMD ["{command}", {docker_command_args}"/opt/pht_train/{entrypoint_file}"]\n'

        docker_file = docker_from + directory_setup + docker_command

        # docker_file = f'''
        #     FROM {self.registry_domain}/master/{master_image}
        #     RUN mkdir /opt/pht_results
        #     RUN mkdir /opt/pht_train
        #     RUN chmod -R +x /opt/pht_train
        #     CMD ["{command}", {docker_command_args}, "/opt/pht_train/{entrypoint_file}"]
        #     '''
        file_obj = BytesIO(docker_file.encode("utf-8"))

        return file_obj

    def _get_service_token(self):
        """
        Gets the service token from vault to allow the train builder to authenticate against the central API

        :return:
        """

        secret = self.vault_client.secrets.kv.v1.read_secret(
            path="TRAIN_BUILDER",
            mount_point="services"
        )
        client_data = secret["data"]
        self.service_key = client_data["clientSecret"]
        self.client_id = client_data["clientId"]


if __name__ == '__main__':
    load_dotenv(find_dotenv())
    client = PHTClient(api_url="https://pht.tada5hi.net/api/pht/trains/")
    builder = TrainBuilder(pht_client=client)
