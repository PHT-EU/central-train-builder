import tarfile
import os
import redis
import docker
import threading
from train_lib.clients import PHTClient


class RabbitMqBuilder:

    def __init__(self):
        self.vault_url = os.getenv("vault_url")
        self.vault_token = os.getenv("vault_token")
        self.registry_url = os.getenv("harbor_url")
        self.redis = None
        self.docker_client = None
        # Setup redis and docker client
        self._setup()

        # Set up Pht client
        # TODO init values
        self.pht_client = PHTClient()


    def _setup(self):
        # Connect to redis either in docker-compose container or on localhost
        try:
            self.redis = redis.Redis("redis", decode_responses=True)
            self.redis.ping()
        except redis.exceptions.ConnectionError as e:
            print("Redis container not found, attempting connection on localhost")
            self.redis = redis.Redis(decode_responses=True)
            print(self.redis.ping())
        # Setup docker client
        self.docker_client = docker.client.from_env()
        login_result = self.docker_client.login(username=os.getenv("harbor_user"), password=os.getenv("harbor_pw"),
                                                registry=self.registry_url)
        print(login_result)

    def build_train(self, message):
        # TODO get message
        #

        pass



