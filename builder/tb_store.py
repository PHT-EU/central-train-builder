from typing import List
from redis import Redis
from loguru import logger
from enum import Enum
from hvac import Client
from pydantic import BaseModel

from builder.messages import BuildStatus


class VaultUserPublicKey(BaseModel):
    user_id: str
    rsa_public_key: str
    paillier_public_key: str


class VaultStationPublicKey(BaseModel):
    station_id: str
    rsa_station_public_key: str


class BuilderVaultStore:
    client: Client

    def __init__(self, vault_client: Client):
        self.client = vault_client

    def get_user_public_key(self, user_id: str) -> VaultUserPublicKey:
        # get data from vault
        user_pk = self.client.secrets.kv.v1.read_secret(
            path=user_id,
            mount_point="user_pks",
        )
        print(user_pk)
        return VaultUserPublicKey(user_id=user_id, **user_pk["data"])

    def get_user_public_keys(self, user_ids: List[str]) -> List[VaultUserPublicKey]:
        user_pks = []
        for user_id in user_ids:
            user_pks.append(self.get_user_public_key(user_id))

        return user_pks

    def get_station_public_key(self, station_id: str) -> VaultStationPublicKey:
        station_pk = self.client.secrets.kv.v1.read_secret(
            path=station_id,
            mount_point="user_pks",
        )
        print(station_pk)
        return VaultStationPublicKey(station_id=station_id, **station_pk["data"])

    def get_station_public_keys(self, station_ids: List[str]) -> List[VaultStationPublicKey]:
        station_pks = []
        for station_id in station_ids:
            station_pks.append(self.get_station_public_key(station_id))
        return station_pks


class BuilderRedisStore:
    redis: Redis

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def train_exists(self, train_id: str) -> bool:
        return self.redis.exists(f"{train_id}-buildStatus") == 1

    def get_build_status(self, train_id: str) -> BuildStatus:
        return self.redis.get(f"{train_id}-buildStatus")

    def set_build_status(self, train_id: str, status: BuildStatus) -> None:
        self.redis.set(f"{train_id}-buildStatus", status.value)
