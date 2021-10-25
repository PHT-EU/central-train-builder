import os
import tarfile
from enum import Enum

import docker
import redis
import requests
from train_lib.clients import PHTClient
from io import BytesIO
from docker.models.containers import Container
import json
from tarfile import TarInfo, TarFile
import time
from dotenv import load_dotenv, find_dotenv
import logging
from loguru import logger
from hvac import Client

LOGGER = logging.getLogger(__name__)


class BuildStatus(Enum):
    STARTED = "trainBuildStarted"
    FAILED = "trainBuildFailed"
    FINISHED = "trainBuildFinished"
    NOT_FOUND = "trainNotFound"
    STOPPED = "trainBuildStopped"


class RabbitMqBuilder:

    def __init__(self, pht_client: PHTClient):
        load_dotenv(find_dotenv())
        self.vault_url = os.getenv("VAULT_URL")
        self.vault_token = os.getenv("VAULT_TOKEN")
        self.registry_url = os.getenv("HARBOR_URL")
        self.redis = None
        self.docker_client = None
        # Setup redis and docker client
        self.service_key = None
        self.client_id = None
        self._setup()

        assert self.vault_url and self.vault_token and self.registry_url

        self.vault_client = Client(
            url=os.getenv("VAULT_URL"),
            token=os.getenv("VAULT_TOKEN")
        )

        # Set up Pht client
        self.pht_client = pht_client

    def _setup(self):
        """
        Ensure that the docker client has access to the harbor repository

        :return:
        """
        # Connect to redis either in docker-compose container or on localhost
        logger.info("Initializing docker client and logging into registry")
        self.docker_client = docker.client.from_env()
        login_result = self.docker_client.login(username=os.getenv("HARBOR_USER"), password=os.getenv("HARBOR_PW"),
                                                registry=self.registry_url)
        logger.info(f"Login result -- {login_result['Status']}")

        logger.info("Requesting service token")
        self._get_service_token()
        logger.info("Service token obtained")

        logger.info("Connecting to redis")
        self.redis = redis.Redis(host=os.getenv("REDIS_HOST", None), decode_responses=True)
        logger.info("Validating setup")
        self._validate_setup()
        logger.info("Setup complete")

    def build_train(self, build_data: dict, meta_data: dict):
        """
        Builds the train based two dictionaries containing build and metadata

        :param build_data:
        :param meta_data:
        :return:
        """

        # pull master image
        registry = os.getenv("HARBOR_URL").split("//")[-1]
        master_image = f"{registry}/{build_data['masterImage']}"
        logger.info(f"Train: {build_data['trainId']} -- Pulling master image {master_image}...")
        self.docker_client.images.pull(master_image, tag="latest")

        # try:
        docker_file_obj = self._make_dockerfile(
            master_image=build_data["masterImage"],
            executable=build_data["entrypointExecutable"],
            entrypoint_file=build_data["entrypointPath"])

        logger.info(f"Train: {build_data['trainId']} -- Building base image")
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

    def _make_train_config(self, build_data: dict, meta_data: dict):
        """
        Generate a tar archive containing a json file train_config.json in which the relevant security values for the
        train will be stored

        :param build_data: dictionary containing build data sent from the central ui
        :param meta_data:
        :return:
        """

        logger.info(f"Train: {build_data['trainId']} -- Generating train config")

        user_public_key = self.pht_client.get_user_pk(build_data["userId"])

        station_public_keys = self.pht_client.get_multiple_station_pks(build_data["stations"])
        registry = os.getenv("HARBOR_URL").split("//")[-1]
        master_image = f"{registry}/{build_data['masterImage']}"

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
        self.docker_client.images.remove(repo + ":base", noprune=False)
        self.docker_client.images.remove(repo + ":latest", noprune=False)

    @staticmethod
    def _make_dockerfile(master_image: str, executable: str, entrypoint_file: str):
        registry = os.getenv("HARBOR_URL").split("//")[-1]
        if executable in ["r", "R"]:
            executable = "Rscript"
        docker_file = f'''
            FROM {registry}/{master_image}
            RUN mkdir /opt/pht_results
            RUN mkdir /opt/pht_train
            RUN chmod -R +x /opt/pht_train
            CMD ["{executable}", "/opt/pht_train/{entrypoint_file}"]
            '''
        file_obj = BytesIO(docker_file.encode("utf-8"))

        return file_obj

    def _get_service_token(self):
        """
        Gets the service token from vault to allow the train builder to authenticate against the central API

        :return:
        """
        vault_token = os.getenv("VAULT_TOKEN")
        vault_url = os.getenv("VAULT_URL")

        if vault_url[-1] != "/":
            vault_url = vault_url + "/"
        url = vault_url + "v1/services/TRAIN_BUILDER"
        headers = {"X-Vault-Token": vault_token}
        r = requests.get(url=url, headers=headers)
        r.raise_for_status()

        client_data = r.json()["data"]
        self.service_key = client_data["clientSecret"]
        self.client_id = client_data["clientId"]


if __name__ == '__main__':
    load_dotenv(find_dotenv())
    client = PHTClient(api_url="https://pht.tada5hi.net/api/pht/trains/")
    builder = RabbitMqBuilder(pht_client=client)
