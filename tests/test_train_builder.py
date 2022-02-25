import os
import pprint

import pytest
from dotenv import load_dotenv, find_dotenv
from hvac import Client
from pydantic import ValidationError

from builder.TrainBuilder import TrainBuilder
from builder.messages import BuildMessage, BuildStatus, BuilderCommands
from builder.tb_store import VaultEngines


@pytest.fixture
def test_user_id():
    return "tb-test-user"


@pytest.fixture
def test_station_ids():
    return [f"tb-test-station-{i + 1}" for i in range(3)]


@pytest.fixture
def build_msg(test_user_id, test_station_ids):
    msg_dict = {
        "id": "f54f58d9-58a1-4141-9dfb-a48b2a275998",
        "type": "trainBuildStart",
        "metadata": {},
        "data": {
            "user_id": test_user_id,
            "user_rsa_secret_id": "rsa-test",
            "id": "da8fd868-0fed-42e3-b6d8-5abbf0864d4a",
            "proposal_id": 4,
            "stations": [
                "1"
            ],
            "files": [
                "test_train/entrypoint.py",
                "test_train/requirements.txt"
            ],
            "master_image": "python/slim",
            "entrypointExecutable": "python",
            "entrypoint_path": "test_train/entrypoint.py",
            "session_id": "8203c4facff907d3bd83f8399e9a97aa4270e27acb4369f5bcdaab20643f2dc7c2ca8fe78a576c3ae7ac56b64d89a778aa86f7f90360734965dce0264ddcd705",
            "hash": "91416369e845e7ff12efe8514736d468b71bfc15cc5ded92399a1a558f4317da68cfd5884cb9e5bbbac15ce45731afe4e47ced256c7a2e493ff7fad5481b8d31",
            "hash_signed": "ace71ecae217b8da4426cee8ba8abeddab6d1d9c9d073e7c54197b82a1d453189ca2a3e278be7747b4e0fac28bba32dc1b5a4dbc4b060a2f5e659180367b56b90b6ee8f59f529206e39645acd0bd24c03c3ef291ac8ad91dbf4390541033656ec3ee48a516a94348cb60ed596be305c3754e7e4b66dc433bb47a2483ea7d772cc6a353bb43b82e4f35f7dc6ee1f502765d64785ea816b20eed6c3a1ea857a753d5048e16d395d3479b62d91c9870d9f19ee0740b6051a3089e5350227820281406d267e188ac4edb1f0f3ebd36a0aa6cb2eeeaaa71023b0e8e6381d3bc683277208a7c91de77d61e4a8ca8f71621449e564f57bb8eaef25f08da61e8b0b79f61",
            "query": {
                "query": "/Patient?",
                "data": {
                    "output_format": "json",
                    "filename": "patients.json",
                }
            },
            "user_he_key": "12345241",
            "entrypoint_command": "run"
        }
    }
    return BuildMessage(**msg_dict["data"])


@pytest.fixture
def train_files():
    # todo generate tar file
    pass


@pytest.fixture
def builder():
    load_dotenv(find_dotenv())
    builder = TrainBuilder()
    return builder


def test_initialization_and_setup():
    load_dotenv(find_dotenv())

    tb = TrainBuilder()


def test_get_service_token(builder):
    key = builder.service_key
    client_id = builder.client_id

    assert key, client_id

    builder._get_service_credentials()

    assert builder.service_key == key
    assert builder.client_id == client_id


def test_make_docker_file(builder):
    master_image = "python/base"
    command = "python"
    args = ["-c", "print('hello world')"]
    entrypoint_file = "entrypoint.sh"
    entrypoint_file_prefixed = "./entrypoint.sh"
    train_dir = "/opt/pht_train"
    results_dir = "/opt/pht_results"

    docker_from = f"FROM {builder.registry_domain}/master/{master_image}\n"
    directory_setup = f"RUN mkdir {train_dir} && mkdir {results_dir} && chmod -R +x {train_dir} \n"
    docker_command_args = [f'"{arg}"' for arg in args]
    docker_command_args = ", ".join(docker_command_args)
    docker_command = f'CMD ["{command}", {docker_command_args}, "/opt/pht_train/{entrypoint_file}"]\n'
    docker_file = docker_from + directory_setup + docker_command

    docker_command_no_args = f'CMD ["{command}", "/opt/pht_train/{entrypoint_file}"]\n'
    docker_file_no_args = docker_from + directory_setup + docker_command_no_args

    docker_file_obj = builder._make_dockerfile(
        master_image=master_image,
        command=command,
        command_args=args,
        entrypoint_file=entrypoint_file)
    assert docker_file == docker_file_obj.read().decode("utf-8")

    docker_file_obj_prefixed = builder._make_dockerfile(
        master_image=master_image,
        command=command,
        command_args=args,
        entrypoint_file=entrypoint_file_prefixed)

    assert docker_file == docker_file_obj_prefixed.read().decode("utf-8")

    docker_file_obj_no_args = builder._make_dockerfile(
        master_image=master_image,
        command=command,
        command_args=None,
        entrypoint_file=entrypoint_file_prefixed)

    assert docker_file_no_args == docker_file_obj_no_args.read().decode("utf-8")

    # print(docker_file_obj.read().decode("utf-8"))
    docker_file_obj.seek(0)
    image, logs = builder.docker_client.images.build(fileobj=docker_file_obj)

    assert image

    print(image, list(logs))


def test_process_status_message(builder):
    train_id = "tb-test-train-id"
    builder._setup()
    builder.redis_store.set_build_status(train_id=train_id, status=BuildStatus.STARTED)
    message = {
        "type": "trainBuildStatus",
        "data": {
            "id": train_id,
        }
    }

    response = builder.process_message(message)

    assert response.type == BuildStatus.STARTED

    # train not found
    message = {
        "type": "trainBuildStatus",
        "data": {
            "id": "wrong-id",
        }
    }

    response = builder.process_message(message)
    assert response.type == BuildStatus.NOT_FOUND


def test_generate_config(builder, build_msg):
    # generate test user and secrets in vault
    user_secrets = {
        "rsa-test": os.urandom(32).hex(),
    }

    builder.vault_client.secrets.kv.v1.create_or_update_secret(
        path=str(build_msg.user_id),
        mount_point=VaultEngines.USERS.value,
        secret=user_secrets
    )

    for station_id in build_msg.stations:
        station_secret = {
            "rsa_public_key": station_id.encode().hex(),
        }
        response = builder.vault_client.secrets.kv.v1.create_or_update_secret(
            path=station_id,
            mount_point=VaultEngines.STATIONS.value,
            secret=station_secret
        )
        print(response.text)

    config, query = builder.generate_config_and_query(build_msg)

    assert config.user_keys.rsa_public_key == user_secrets["rsa-test"]

    assert config


def test_build(builder, build_msg):
    # train id not found
    invalid_msg = {
        "type": "trainBuildStart",
        "data": {
            "hello": "random"
        }
    }

    response = builder.process_message(invalid_msg)
    assert response.type == BuildStatus.NOT_FOUND

    # invalid build data
    invalid_msg = {
        "type": "trainBuildStart",
        "data": {
            "id": "random",
            "hello": "world"
        }
    }


    response = builder.process_message(invalid_msg)
    assert response.type == BuildStatus.FAILED

