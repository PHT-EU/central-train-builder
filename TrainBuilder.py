import docker
import pickle
import requests
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import json
from base64 import b64encode
from simulate_webservice import create_json_message
import tempfile
import shutil
from dotenv import load_dotenv
import subprocess
import redis


class TrainBuilder:
    def __init__(self):
        # docker login
        env_path = ".env"
        load_dotenv(env_path)
        self.vault_url = os.getenv("vault_url")
        self.vault_token = os.getenv("vault_token")
        self.hash = None
        self.registry_url = os.getenv("harbor_url")
        self.session_id = None
        self.redis = redis.Redis(decode_responses=True)

    def build_train(self, web_service_json:dict):
        """
        Build a train based on the message sent from the UI, also generates a configuration file containing relevant
        values for encryption

        :param web_service_json: The content of the message received from the webservice
        :return: docker image of the final train
        """

        # Generate random number for session id, is this the right place?
        # session_id = os.urandom(64)
        # TODO encrypt the query files before adding them to the image
        session_key = Fernet.generate_key()

        message = web_service_json
        self.create_train_config(message["user_id"],
                                 message["user_public_key"],
                                 message["user_signature"],
                                 session_key,
                                 message["route"],
                                 message["train_id"])

        # login to the registry
        client = docker.client.from_env()
        env_path = '.env'
        load_dotenv(dotenv_path=env_path)
        print(os.getenv("harbor_user"))

        client = docker.client.from_env()
        try:
            login_result = client.login(username=os.getenv("harbor_user"), password=os.getenv("harbor_pw"),
                                        registry=self.registry_url)
            # print(login_result)
        except Exception as e:
            print(e)
            self._cleanup()
            return {"success": False, "msg": "Docker login error"}

        try:
            login_result = client.login(username=os.getenv("harbor_user"), password=os.getenv("harbor_pw"),
                                        registry=self.registry_url)
            print(login_result)
        except Exception as e:
            self._cleanup()
            print("Train Builder login error")
            print(e)

        # Generate a dockerfile and the directory structure based on the message
        self.create_temp_dockerfile(message, "train_config.json")
        image, logs = client.images.build(path=os.getcwd())
        repo = f"harbor.personalhealthtrain.de/pht_incoming/{message['train_id']}"
        image.tag(repo, tag="base")
        # Remove files after image has been built successfully
        self._cleanup()
        result = client.images.push(repository=repo,
                                    tag="base")
        # print(result)
        # TODO remove image after pushing successfully
        return {"success": True, "msg": "Successfully built train"}

    @staticmethod
    def _cleanup():
        """
        Remove the files generated while building a train

        """
        os.remove("train_config.json")
        shutil.rmtree("pht_train")
        if os.path.isdir("pht_train"):
            os.rmdir("pht_train")


    def build_example(self, data):
        """
        Build minimal example
        :param data: The message received from train submission
        :return: success response based on execptions
        """
        endpoints = data["endpoint"]
        files = endpoints["files"]
        file_name = files[0]["name"]
        file_content = files[0]["content"]

        path = "./"
        file_path = path + file_name

        train_id = data["train_id"]
        # name = "train_id_" + str(train_id)
        name = str(train_id)
        with open(file_path, "w") as f:
            f.write(file_content)

        subprocess.Popen(["chmod", "+x", file_path])  # in order to exec
        # master_image = data["master_image"] # Provice Peter with harbor credentials
        master_image = "harbor.personalhealthtrain.de/pht_master/python_train:latest"
        train_path = "/opt/pht_train/endpoints/minimaltrain/commands/run/" + file_name

        with open("Dockerfile", "w", encoding='utf-8') as f:
            f.write(f'FROM ' + master_image + '\n')
            f.write(f'COPY {file_path} {train_path}\n')
            f.write(f'ENTRYPOINT ["python", "{train_path}"]')

        client = docker.client.from_env()
        try:
            login_result = client.login(username=os.getenv("harbor_user"), password=os.getenv("harbor_pw"),
                                        registry=self.registry_url)
            #print(login_result)
        except Exception as e:
            print(e)
            return {"success": False, "msg": "Docker login error"}

        # todo pull image if not available
        repo = f"harbor.personalhealthtrain.de/pht_incoming/{name}"
        image, logs = client.images.build(path=os.getcwd())
        image.tag(repo, tag="base")  # in order to be processed by train router
        os.remove("Dockerfile")
        os.remove(file_path)
        # todo remove image afterwards
        try:
            result = client.images.push(repository=repo)
            print(result)
            return {"success": True, "msg": "Successfully built train"}
        except Exception as e:
            print(e)
            return {"success": False, "msg": "Docker push error"}

    def provide_hash(self, web_service_json):
        """
        Calculates the hash based on the user provided files and returns it for signing by the user
        :param web_service_json:
        :return:
        """
        # TODO check this session id for correctness
        session_id = self._generate_session_id()
        self.session_id = session_id
        # files = self._get_files(web_service_json)
        files = web_service_json["endpoint"]["files"]
        route = web_service_json["route"]
        try:
            train_hash = self.generate_hash(web_service_json["user_id"], files, route, session_id)
            print("Adding hash to redis")
            self.redis.set(web_service_json['train_id'], value=self.hash)
            print(f"Redis Hash value: {self.redis.get(web_service_json['train_id'])}")
            self.hash = None
            return {"success": True, "data": {"hash": train_hash}}
        except BaseException as e:
            print(e)
            return {"success": False, "msg": ""}

    def create_temp_dockerfile(self, web_service_json, train_config):
        """
        Creates a dockerfile to build a train image
        :param endpoints: Dictionary created from message from webservice containing  all files defining the file
        structure of the train
        :return:
        """
        with open("Dockerfile", "w") as f:
            f.write("FROM " + web_service_json["master_image"] + "\n")
            self.generate_pht_dir(web_service_json)
            f.write("COPY pht_train /opt/pht_train\n")
            f.write("COPY " + train_config + " " + "/opt/pht_train/train_config.json" + "\n")

    @staticmethod
    def encrypt_file(fernet: Fernet, file):
        """
        Encrypts a file using a provided cryptography fernet object
        :param fernet:
        :param file:
        :return:
        """
        with open(file, "rb") as f:
            encrypted_file = fernet.encrypt(f.read())
        with open(file, "wb") as f:
            f.write(encrypted_file)

    def create_train_config(self, user_id: int, user_pk: str, user_signature, session_key, route, train_id):
        """
        Creates a keyfile given the values provided by the webservice and stores it in the current working  directory
        :param user_id: id of the user creating the train
        :param user_pk: public key provided by the user bytes in PEM format
        :param user_signature: signature created with the offline tool using the users private key
        :return:
        """

        station_public_keys = self.get_station_public_keys(route)
        print(station_public_keys)
        encrypted_session_key = self.encrypt_session_key(session_key, station_public_keys)
        # TODO check types of signatures/keys
        keys = {
            "user_id": user_id,
            "train_id": train_id,
            "session_id": b64encode(os.urandom(64)).decode(),
            "rsa_user_public_key": user_pk,
            "encrypted_key": encrypted_session_key,
            "rsa_public_keys": station_public_keys,
            "e_h": self.redis.get(train_id),
            "e_h_sig": user_signature,
            "e_d": None,
            "e_d_sig": None,
            "digital_signature": None
        }

        with open("train_config.json", "w") as kf:
            json.dump(keys, kf, indent=2)

    def encrypt_session_key(self, session_key, station_public_keys):
        """
        Encrypts the generated symmetric key with all public keys of the stations on the route
        :param session_key:
        :param route:
        :return:
        """
        encrypted_session_key = {}
        for idx, key in station_public_keys.items():
            pk = self.load_public_key(key.encode())
            encrypted_key = pk.encrypt(session_key,
                                       padding.OAEP(
                                           mgf=padding.MGF1(algorithm=hashes.SHA512()),
                                           algorithm=hashes.SHA512(),
                                           label=None
                                       ))
            encrypted_session_key[idx] = b64encode(encrypted_key).decode()

        return encrypted_session_key

    def get_station_public_keys(self, route: list):
        """
        Gets the public keys of the stations included in the route from the vault service
        :param route: route containing PID of stations
        :return: dictionary with statino PIDs as keys and the associated public keys as values
        """
        public_keys = {}
        for station in route:
            public_keys[station] = self.get_station_public_key(station)
        return public_keys

    def get_station_public_key(self, station_id):
        """
        Get
        :param station_id:
        :type station_id:
        :return:
        :rtype:
        """
        url = self.vault_url
        vault_url = f"{url}v1/station_pks/{station_id}"
        headers = {"X-Vault-Token": self.vault_token}
        r = requests.get(vault_url, headers=headers)
        data = r.json()["data"]
        print(data)
        return data["data"]["rsa_public_key"]

    def get_user_public_key(self, user_id):
        """
        Get
        :param user_id:
        :return:
        """
        token = self.vault_token
        url = self.vault_url
        vault_url = f"{url}v1/user_pks/{user_id}"
        headers = {"X-Vault-Token": token}
        r = requests.get(vault_url, headers=headers)
        data = r.json()["data"]
        return data["data"]["rsa_public_key"]

    @staticmethod
    def load_public_key(key: bytes):
        """
        Load a public from its bytes representation in PEM format
        :param key: byte object of a public RSA key stored in PEM format
        :return: public key object used for RSA encryption
        """
        public_key = serialization.load_pem_public_key(key, backend=default_backend())
        return public_key

    @staticmethod
    def _generate_session_id():
        return os.urandom(64)

    @staticmethod
    def _get_files(message):
        """
        Gets the paths (on the server) of all specified files
        :param message: json message received from the webserver
        :return: list of file paths of relevant files
        """
        files = []
        for endpoint in message["endpoints"]:
            for command in endpoint["commands"]:
                for f in command["files"]:
                    files.append(f[1])

        return files

    @staticmethod
    def generate_pht_dir(message):
        """
        Parses the message received from the webservice and  returns  a list of all files to be hashed
        :param message:
        :return: list of files to be hashed
        """
        # Generate the directory structure TODO support multiple commands/endpoints
        base_path = "pht_train"
        os.mkdir(base_path)
        ep_dir = os.path.join(base_path, 'endpoints')
        os.mkdir(ep_dir)
        ep_path = os.path.join(base_path, 'endpoints', message['endpoint']['name'])
        os.mkdir(ep_path)
        command_path = os.path.join(base_path,'endpoints', message['endpoint']['name'], message['endpoint']['command'])
        os.mkdir(command_path)

        for file in message["endpoint"]['files']:
            file_path = os.path.join(command_path, file["name"])
            with open(file_path, "w") as f:
                f.write(file['content'])

        # for query_file in message["query_files"]:
        #    files.append((query_file, os.path.join(query_prefix, query_file)))

    def generate_hash(self, user_id, files, route, session_id):
        """

        :param user_id: String value of the user id
        :param files: files to be hashed (algorithm and query files)
        :param route: route containing PIDs of stations included in the analysis
        :param session_id: session id randomly created by TB
        :return: hash value to be signed offline by user
        """
        hasher = hashes.Hash(hashes.SHA512(), default_backend())
        hasher.update(str(chr(user_id)).encode())
        self.hash_files(hasher, files)
        hasher.update(bytes(route))
        hasher.update(session_id)
        digest = hasher.finalize()
        self.hash = digest.hex()
        return self.hash

    @staticmethod
    def hash_files(hasher: hashes.Hash, files: list):
        for file in files:
            hasher.update(file["content"].encode())

    def _get_hash(self):
        if self.hash is not None:
            return self.hash
        else:
            print("No Hash available yet for the current train")


if __name__ == '__main__':
    tb = TrainBuilder()
    # keys = tb.get_station_public_keys([1, 2, 3])
    sym_key = Fernet.generate_key()
    route = [1, 2, 3]
    print(tb.encrypt_session_key(sym_key, route))
    json_message = create_json_message()
    tb.build_train(json_message)
    # tb.generate_pht_dir(json.loads(json_message))
    # keys = tb.create_key_file("123456", )
    # tb._save_key_file(keys)
