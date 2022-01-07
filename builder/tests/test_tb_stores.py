import os

import pytest
from dotenv import load_dotenv, find_dotenv
from redis import Redis
from hvac import Client

from builder.tb_store import BuilderRedisStore, BuilderVaultStore


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
    print(f"VAULT_URL: {vault_url}, VAULT_TOKEN: {vault_token}")
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
        mount_point="user_pks",
        secret=test_user_pk
    )

    user_pk = vault_store.get_user_public_key(user_id=user_id)

    assert user_pk.user_id == user_id
    assert user_pk.rsa_public_key == test_user_pk['rsa_public_key']
    # delete created secret
    vault_client.secrets.kv.v1.delete_secret(
        path=user_id,
        mount_point="user_pks"
    )

def test_vault_store_get_multiple_user_pks(vault_store, vault_client):
    pass
