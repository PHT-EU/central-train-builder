from typing import List, Optional, Union, Callable, Any
from redis import Redis
from loguru import logger
from enum import Enum
from hvac import Client
from pydantic import BaseModel

from builder.messages import BuildStatus


class VaultEngines(Enum):
    USERS = "user-secrets"
    STATIONS = "stations"
    ROUTES = "routes"


class VaultUserPublicKey(BaseModel):
    user_id: str
    rsa_public_key: str
    paillier_public_key: Optional[str] = None


class VaultStationPublicKey(BaseModel):
    station_id: str
    rsa_public_key: str


class VaultRoute(BaseModel):
    repository_suffix: str
    stations: List[str]
    periodic: Optional[bool] = False
    epochs: Optional[int] = None


class BuilderVaultStore:
    client: Client

    def __init__(self, vault_client: Client):
        self.client = vault_client

    def get_user_public_key(self, user_id: str, rsa_key_id: str, paillier_key_id: str = None) -> VaultUserPublicKey:
        # get data from vault
        user_pk = self.client.secrets.kv.v1.read_secret(
            path=user_id,
            mount_point=VaultEngines.USERS.value,
        )

        return VaultUserPublicKey(
            user_id=user_id,
            rsa_public_key=user_pk["data"].get(rsa_key_id),
            paillier_public_key=user_pk["data"].get(paillier_key_id))

    # def get_user_public_keys(self, user_ids: List[str]) -> List[VaultUserPublicKey]:
    #     user_pks = []
    #     for user_id in user_ids:
    #         user_pks.append(self.get_user_public_key(user_id))
    #
    #     return user_pks

    def get_station_public_key(self, station_id: str) -> VaultStationPublicKey:
        station_pk = self.client.secrets.kv.v1.read_secret(
            path=station_id,
            mount_point=VaultEngines.STATIONS.value,
        )
        rsa_public_key = station_pk["data"].get("rsa_public_key")
        return VaultStationPublicKey(station_id=station_id, rsa_public_key=rsa_public_key)

    def get_station_public_keys(self, station_ids: List[str]) -> List[VaultStationPublicKey]:
        station_pks = []
        for station_id in station_ids:
            station_pks.append(self.get_station_public_key(station_id))
        return station_pks

    def add_route(self, train_id: str, route: VaultRoute):
        json_secret = route.dict()
        # todo improve this
        json_secret["repositorySuffix"] = route.repository_suffix
        del json_secret["repository_suffix"]
        response = self.client.secrets.kv.v1.create_or_update_secret(
            mount_point=VaultEngines.ROUTES.value,
            path=train_id,
            secret=json_secret,
        )
        print(response)


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

    def train_submitted(self, train_id: str) -> bool:
        if self.redis.exists(f"{train_id}-submitted") == 1:
            return True
        else:
            self.redis.set(f"{train_id}-submitted", "true")
            return False
