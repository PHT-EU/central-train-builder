import os

import pytest
from dotenv import load_dotenv, find_dotenv
from redis import Redis
from hvac import Client

from builder.tb_store import BuilderRedisStore, BuilderVaultStore, VaultEngines


@pytest.fixture
def redis_client() -> Redis:
    load_dotenv(find_dotenv())
    redis_host = os.getenv('REDIS_HOST')
    client = Redis(host=redis_host)
    return client


@pytest.fixture
def vault_client() -> Client:
    load_dotenv(find_dotenv())
    vault_url = os.getenv('VAULT_URL')
    vault_token = os.getenv('VAULT_TOKEN')
    client = Client(vault_url, token=vault_token)
    return client


@pytest.fixture
def vault_store(vault_client):
    return BuilderVaultStore(vault_client)


def test_vault_store_get_user_pk(vault_store, vault_client):
    user_id = 'tb-test-user'

    test_user_pk = {
        "rsa_public_key": "public_key",
        "paillier_public_key": "paillier_key"
    }
    vault_client.secrets.kv.v1.create_or_update_secret(
        path=user_id,
        mount_point=VaultEngines.USERS.value,
        secret=test_user_pk
    )

    user_pk = vault_store.get_user_public_key(user_id=user_id, rsa_key_id="rsa_public_key",
                                              paillier_key_id="paillier_public_key")

    assert user_pk.user_id == user_id
    assert user_pk.rsa_public_key == test_user_pk['rsa_public_key']
    # delete created secret
    # vault_client.secrets.kv.v1.delete_secret(
    #     path=user_id,
    #     mount_point=VaultEngines.USERS.value
    # )

# def test_vault_store_get_multiple_user_pks(vault_store, vault_client):
#     # create user secrets
#
#     user_ids = []
#     for i in range(3):
#         user_id = f'tb-test-user-{i}'
#         user_ids.append(user_id)
#         test_user_pk = {
#             "rsa_public_key": f"public_key-{i}",
#             "paillier_public_key": f"paillier_key-{i}"
#         }
#         vault_client.secrets.kv.v1.create_or_update_secret(
#             path=user_id,
#             mount_point="user_pks",
#             secret=test_user_pk
#         )
#
#     user_pks = vault_store.get_user_public_keys(user_ids=user_ids)
#
#     assert user_pks[0].user_id == user_ids[0]
#     assert len(user_pks) == 3
#
#     # delete generated secrets after use
#     for user_id in user_ids:
#         vault_client.secrets.kv.v1.delete_secret(
#             path=user_id,
#             mount_point="user_pks"
#         )
