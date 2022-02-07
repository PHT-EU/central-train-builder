import base64
import os
import tarfile
from enum import Enum

from typing import List, Tuple
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
from pydantic import ValidationError
from requests import HTTPError

from train_lib.clients import PHTClient
from train_lib.security.train_config import TrainConfig, HexString, UserPublicKeys, StationPublicKeys

from builder.messages import QueueMessage, BuilderCommands, BuildMessage, BuilderResponse
from builder.tb_store import BuildStatus, BuilderRedisStore, BuilderVaultStore, VaultRoute

LOGGER = logging.getLogger(__name__)


class TrainPaths(Enum):
    TRAIN_DIR = "/opt/pht_train"
    RESULTS_DIR = "/opt/pht_results"
    CONFIG_PATH = "/opt/train_config.json"
    QUERY_PATH = "/opt/pht_train/query.json"


INCOMING_REPOSITORY = "pht_incoming"


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
    vault_store: BuilderVaultStore = None
    redis_client: redis.Redis = None
    redis_store: BuilderRedisStore = None

    def __init__(self):
        load_dotenv(find_dotenv())
        # Run setup
        self._setup()

        assert self.vault_url and self.vault_token and self.registry_url

    def process_message(self, msg: dict) -> BuilderResponse:

        message = QueueMessage(**msg)

        logger.info(f"Processing message: {message}")
        train_id = message.data.get("id")
        if not train_id:
            logger.error("Train id not found in message")
            status = BuildStatus.NOT_FOUND
            return BuilderResponse(type=status)

        if message.type == BuilderCommands.START:
            try:
                build_message = BuildMessage(**msg["data"])
                logger.debug(f"Build message: {build_message}")
            except ValidationError as e:
                logger.error(f"Invalid build message: {e}")
                status = BuildStatus.FAILED
                return BuilderResponse(type=status, data={"id": train_id, "message": "invalid build message"})
            response = self.build(build_message)
            if response.type == BuildStatus.FINISHED:
                route = self._make_route(train_id, build_message)
                self.vault_store.add_route(train_id, route)
            return response
        elif message.type == BuilderCommands.STOP:
            # todo stop build
            pass
        elif message.type == BuilderCommands.STATUS:
            if self.redis_store.train_exists(train_id):
                status = self.redis_store.get_build_status(train_id=train_id)
            else:
                status = BuildStatus.NOT_FOUND

            return BuilderResponse(type=status, data={"id": train_id})

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

        logger.info("Initializing vault client & store")

        self.vault_url = os.getenv("VAULT_URL")
        self.vault_token = os.getenv("VAULT_TOKEN")

        if not self.vault_url and self.vault_token:
            raise ValueError("Vault url and token must be set in environment variables -> VAULT_URL + VAULT_TOKEN")
        self.vault_client = Client(
            url=self.vault_url,
            token=self.vault_token
        )
        self.vault_store = BuilderVaultStore(self.vault_client)

        logger.info("Vault client initialized")

        logger.info("Requesting service credentials from vault")
        self._get_service_credentials()
        logger.info("Service token obtained")

        self.api_url = os.getenv("UI_TRAIN_API")

        logger.info("Connecting to redis")
        self.redis_host = os.getenv("REDIS_HOST")
        self.redis = redis.Redis(host=self.redis_host, decode_responses=True)
        logger.info("Redis connection established. Setting up store...")
        self.redis_store = BuilderRedisStore(self.redis)
        logger.info("Redis store initialized")
        logger.info("Validating setup")
        self._validate_setup()
        logger.info("Setup complete")

    def build(self, build_message: BuildMessage) -> BuilderResponse:

        # generate the config and query based on the build message
        try:
            logger.info(f"Generating train config from message - Train {build_message.id}")
            config, query = self.generate_config_and_query(build_message)

            # build the base image from the config
            self._ensure_master_image(build_message)
            image, logs = self._build_image(build_message)
            logger.info(f"Train {build_message.id} - Image built - {image.id}. Creating temporary container...")
            logger.debug(f"Build Logs - {list(logs)}")
            container = self.docker_client.containers.create(image.id)
            logger.debug(f"Temporary container created - {container.id}")

            # update the container with config and query
            logger.info(f"Train {build_message.id} - Creating train image...")
            logger.info(f"Train {config.train_id} - Adding config and query")
            config_archive, query_archive = self._make_config_and_query_archive(config, query)
            # add config
            if os.getenv("OLD_CONFIG"):
                config_archive = self._make_train_config_old(build_message=build_message)

            container.put_archive(path="/opt", data=config_archive)
            if query_archive:
                container.put_archive(path=TrainPaths.TRAIN_DIR.value, data=query_archive)
            # get train files and add them to the container
            logger.info(f"Train {config.train_id} - Adding train files")
            train_archive = self.get_train_files_archive(build_message.id)
            container.put_archive(path=TrainPaths.TRAIN_DIR.value, data=train_archive)

            # commit the container, tag it and push it to the registry
            self._submit_train_images(container, build_message.id)

            return BuilderResponse(type=BuildStatus.FINISHED, data={"id": build_message.id})
        except Exception as e:
            logger.error(f"Error building train {build_message.id} - {e}")
            try:
                container.remove(force=True)
            except Exception as e:
                logger.error(f"Error removing container - {e}")
            return BuilderResponse(type=BuildStatus.FAILED, data={"id": build_message.id, "error": str(e)})

    def _make_config_and_query_archive(self, config: TrainConfig, query: dict):

        config_archive = self._make_json_archive(config.dict(), "train_config.json")
        query_archive = None
        if query:
            query_archive = self._make_json_archive(query, "train_config.json")
        else:
            logger.info(f"Train {config.train_id} - No query submitted")
        return config_archive, query_archive

    def _submit_train_images(self, container: Container, train_id: str):
        # tag the container into images
        logger.info(f"Train {train_id} - Committing container")

        repo = f"{self.registry_url.split('//')[-1]}/{INCOMING_REPOSITORY}/{train_id}"
        container.commit(repository=repo, tag="latest")
        container.commit(repository=repo, tag="base")

        # push the images to the registry
        logger.info(f"Train {train_id} - Pushing images to registry")
        push_latest = self.docker_client.images.push(repo, tag="latest")
        push_base = self.docker_client.images.push(repo, tag="base")

        logger.debug(f"Train {train_id} - Pushed latest - {push_latest}")
        logger.debug(f"Train {train_id} - Pushed latest - {push_base}")

        # cleanup images and container
        logger.info(f"Train: {train_id} - Removing train artifacts")
        self.docker_client.images.remove(repo + ":base", noprune=False, force=True)
        self.docker_client.images.remove(repo + ":latest", noprune=False, force=True)
        logger.info(f"Train: {train_id} - Removing temporary container")
        container.remove(force=True)

    @staticmethod
    def _make_json_archive(data: dict, filename: str) -> BytesIO:
        # encode dict as json bytes and create bytes io
        json_data = json.dumps(data, indent=2).encode("utf-8")
        json_file_data = BytesIO(json_data)

        # generate a tar archive from the bytes io and add the fileinfo
        archive = BytesIO()
        tar = tarfile.open(fileobj=archive, mode="w")
        json_file = TarInfo(name=filename)
        json_file.size = json_file_data.getbuffer().nbytes
        json_file.mtime = time.time()
        # add the file content and description
        tar.addfile(json_file, json_file_data)
        tar.close()
        # reset the archive
        archive.seek(0)

        return archive

    def generate_config_and_query(self, build_message: BuildMessage) -> Tuple[TrainConfig, dict]:

        logger.info(f"Generating config for Train {build_message.id}")
        config = TrainConfig.construct()

        # transcribe values from build message
        config.train_id = build_message.id
        config.master_image = build_message.master_image
        config.user_id = build_message.user_id
        config.immutable_file_list = build_message.files
        config.immutable_file_hash = build_message.hash
        config.immutable_file_signature = build_message.hash_signed

        # get the station and user keys
        config.user_keys = self._get_user_keys(
            user_id=build_message.user_id,
            rsa_key_id=build_message.user_rsa_secret_id,
            pallier_key_id=build_message.user_paillier_secret_id
        )
        config.station_public_keys = self._get_public_keys_for_stations(build_message.stations)

        config.proposal_id = build_message.proposal_id
        config.session_id = build_message.session_id
        # validate config
        config = TrainConfig(**config.dict())

        return config, build_message.query

    def _ensure_master_image(self, build_message: BuildMessage):
        logger.info(f"Ensuring master image - {build_message.master_image} is available...")
        master_image_repo = self._make_master_image_tag(build_message.master_image)
        self.docker_client.images.pull(master_image_repo, tag="latest")

    def _get_user_keys(self, user_id: str, rsa_key_id: str, pallier_key_id: str = None) -> UserPublicKeys:
        vault_key = self.vault_store.get_user_public_key(user_id, rsa_key_id, pallier_key_id)
        user_keys = UserPublicKeys(
            user_id=user_id,
            paillier_public_key=vault_key.paillier_public_key,
            rsa_public_key=vault_key.rsa_public_key,
        )
        return user_keys

    def _get_public_keys_for_stations(self, station_ids: List[str]) -> List[StationPublicKeys]:
        station_pks = []
        vault_keys = self.vault_store.get_station_public_keys(station_ids)
        for key in vault_keys:
            station_pks.append(
                StationPublicKeys(
                    station_id=key.station_id,
                    rsa_public_key=key.rsa_public_key,
                )
            )
        return station_pks

    def _make_master_image_tag(self, master_image: str):
        return f"{self.registry_domain}/master/{master_image}"

    def _build_image(self, build_message: BuildMessage):

        logger.info(f"Building base image for Train - {build_message.id}")
        docker_file_obj = self._make_dockerfile(
            master_image=build_message.master_image,
            command_args=build_message.entrypoint_command_arguments,
            entrypoint_file=build_message.entrypoint_path,
            command=build_message.entrypoint_command,
        )
        image, logs = self.docker_client.images.build(fileobj=docker_file_obj)
        return image, logs

    def _validate_setup(self):
        fields = vars(self)

        for key in fields:
            if not fields[key]:
                raise ValueError(f"Instance variable {key} could not be initialized.")

    def get_train_files_archive(self, train_id: str) -> BytesIO:

        logger.info(f"Train: {train_id} -- Getting files from central API")
        try:
            train_archive = self._get_tar_archive_from_api(train_id)
        except HTTPError:
            logger.error(f"Error getting train files from central API")
            logger.info(f"Attempting to refresh service credentials")
            self._get_service_credentials()
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
        url = f"{self.api_url}/trains/{train_id}/files/download"
        headers = self._create_api_headers()
        with requests.get(url, headers=headers, stream=True) as r:
            print(r.text)
            r.raise_for_status()
            file_obj = BytesIO()
            for chunk in r.iter_content():
                file_obj.write(chunk)
            file_obj.seek(0)

        return file_obj

    def _create_api_headers(self) -> dict:

        token = self.redis_store.get_cached_token()
        if not token:
            token_url = f"{self.api_url}/token"
            logger.info(f"No token found in cache. Attempting to refresh token from {token_url}")
            r = requests.post(f"{self.api_url}/token", data={"id": self.client_id, "secret": self.service_key})
            logger.debug(f"Token refresh response: {r.text}")
            token = r.json()["access_token"]
        else:
            logger.info(f"Found token in cache. Using cached token")
        headers = {"Authorization": f"Bearer {token}"}
        return headers

    def _make_dockerfile(self, master_image: str, command: str, entrypoint_file: str, command_args: List[str] = None):

        train_dir = TrainPaths.TRAIN_DIR.value
        results_dir = TrainPaths.RESULTS_DIR.value

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

        file_obj = BytesIO(docker_file.encode("utf-8"))

        return file_obj

    def _get_service_credentials(self):
        """
        Gets the service token from vault to allow the train builder to authenticate against the central API

        :return:
        """

        secret = self.vault_client.secrets.kv.v1.read_secret(
            path="TRAIN_BUILDER",
            mount_point="robots"
        )
        client_data = secret["data"]
        self.service_key = client_data["secret"]
        self.client_id = client_data["id"]

    def _make_route(self, train_id: str, build_message: BuildMessage):
        # todo add periodic options
        route = VaultRoute(
            repository_suffix=train_id,
            stations=build_message.stations,
        )
        return route

    def _make_train_config_old(self, build_message: BuildMessage = None):
        """
        Generate a tar archive containing a json file train_config.json in which the relevant security values for the
        train will be stored

        :param build_data: dictionary containing build data sent from the central ui
        :param meta_data:
        :return:
        """

        logger.info(f"Train: {build_message.id} -- Generating train config")

        user_keys = self._get_user_keys(
            user_id=build_message.user_id,
            rsa_key_id=build_message.user_rsa_secret_id,
            pallier_key_id=build_message.user_paillier_secret_id
        )

        station_public_keys = self._get_public_keys_for_stations(build_message.stations)

        station_pks = {spk.station_id: spk.rsa_public_key for spk in station_public_keys}

        config = {
            "master_image": build_message.master_image,
            "user_id": build_message.user_id,
            "train_id": build_message.id,
            "session_id": build_message.session_id,
            "rsa_user_public_key": user_keys.rsa_public_key,
            "encrypted_key": None,
            "rsa_public_keys": station_pks,
            "e_h": build_message.hash,
            "e_h_sig": build_message.hash_signed,
            "e_d": None,
            "e_d_sig": None,
            "digital_signature": None,
            "proposal_id": build_message.proposal_id,
            "user_he_key": user_keys.rsa_public_key,
            "immutable_file_list": build_message.files
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
