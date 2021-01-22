import os
import tarfile

import docker
from train_lib.clients import PHTClient
from io import BytesIO
from docker.models.containers import Container
import json
from tarfile import TarInfo
import time
from dotenv import load_dotenv, find_dotenv
import logging

LOGGER = logging.getLogger(__name__)


class RabbitMqBuilder:

    def __init__(self, pht_client: PHTClient):
        load_dotenv(find_dotenv())
        self.vault_url = os.getenv("vault_url")
        self.vault_token = os.getenv("vault_token")
        self.registry_url = os.getenv("harbor_url")
        self.redis = None
        self.docker_client = None
        # Setup redis and docker client
        self._setup()

        # Set up Pht client
        # TODO init values
        self.pht_client = pht_client
        LOGGER.info("Train Builder setup finished")

    def _setup(self):
        # Connect to redis either in docker-compose container or on localhost
        self.docker_client = docker.client.from_env()
        login_result = self.docker_client.login(username=os.getenv("harbor_user"), password=os.getenv("harbor_pw"),
                                                registry=self.registry_url)

    def build_train(self, build_data: dict, meta_data: dict):

        try:
            docker_file_obj = self._make_dockerfile(
                master_image=build_data["masterImage"],
                executable=build_data["entrypointExecutable"],
                entrypoint_file=build_data["entrypointPath"])

            # Build the image based on the specifications passed in the message
            image, logs = self.docker_client.images.build(fileobj=docker_file_obj)
            # Start a temporary container
            container = self.docker_client.containers.create(image.id)
            # Generate the train config file and query
            config_archive = self._make_train_config(build_data, meta_data)
            query_archive = None
            if build_data["query"]:
                query_archive = self._make_query(build_data["query"])
            # Add files from API to container
            self._add_train_files(container, build_data["trainId"], config_archive, meta_data["token"], query_archive)
            self._tag_and_push_images(container, build_data["trainId"])
            # Post route to vault to start processing
            self.pht_client.post_route_to_vault(build_data["trainId"], build_data["stations"])
            LOGGER.info(f"Successfully built train - {build_data['trainId']}")

        except Exception as e:
            LOGGER.error(f"Error building train \n {e}")
            return 1, "error building train"

        return 0, "train successfully built"

    def _add_train_files(self, container: Container, train_id, config_archive, token, query_archive=None):

        LOGGER.info("Adding train files to container")
        # Get the train files from pht API
        train_archive = self.pht_client.get_train_files_archive(train_id=train_id, token=token)
        container.put_archive("/opt/pht_train", train_archive)
        container.wait()
        container.put_archive("/opt", config_archive)
        if query_archive:
            container.put_archive("/opt", query_archive)

    def _make_train_config(self, build_data, meta_data):
        LOGGER.info("Generating train config")
        user_public_key = self.pht_client.get_user_pk(build_data["userId"])
        station_public_keys = self.pht_client.get_multiple_station_pks(build_data["stations"])

        config = {
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
            "user_he_key": build_data.get("user_he_key", None)
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

    def _make_query(self, query):
        query = BytesIO(json.dumps(json.loads(query)).encode("utf-8"))
        query_archive = BytesIO()
        tar = tarfile.open(fileobj=query_archive, mode="w")
        query_file = TarInfo(name="train_config.json")
        query_file.size = query.getbuffer().nbytes
        query_file.mtime = time.time()
        tar.addfile(query_file, query)
        tar.close()
        query_archive.seek(0)

        return query_archive

    def _tag_and_push_images(self, container, train_id):
        repo = f"harbor.personalhealthtrain.de/pht_incoming/{train_id}"
        container.commit(repo, tag="latest")
        container.commit(repo, tag="base")
        push_latest = self.docker_client.images.push(repo, tag="latest")
        push_base = self.docker_client.images.push(repo, tag="base")
        self.docker_client
        # remove images after building
        self.docker_client.images.remove(repo + ":base")
        self.docker_client.images.remove(repo + ":latest")

    @staticmethod
    def _make_dockerfile(master_image: str, executable: str, entrypoint_file: str):
        docker_file = f'''
            FROM harbor.personalhealthtrain.de/pht_master/master:{master_image}
            RUN mkdir /opt/pht_results
            CMD ["{executable}", "/opt/pht_train/{entrypoint_file}"]
            '''
        file_obj = BytesIO(docker_file.encode("utf-8"))
        return file_obj
