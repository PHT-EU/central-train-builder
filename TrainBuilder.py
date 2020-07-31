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
from pathlib import Path


class TrainBuilder:
    def __init__(self, vault_url):
        # docker login
        # TODO remove vault url and change vault access
        env_path = Path('.') / '.env'
        load_dotenv(dotenv_path=env_path)
        self.vault_url = vault_url
        self.vault_token = os.getenv("vault_token")
        print(self.vault_token)
        self.hash = None
        self.registry_url = "https://harbor.pht.medic.uni-tuebingen.de"
        self.session_id = None

    def build_train(self, web_service_json):
        """
        :param web_service_json: The message received from the
        :return: docker image of the final train
        """

        # Generate random number for session id, is this the right place?
        # session_id = os.urandom(64)
        # # encrypt the query files before adding them to the image
        session_key = Fernet.generate_key()

        message = json.loads(web_service_json)

        train_hash = self.provide_hash(message)

        # fernet = Fernet(session_key)

        # create trainconfig and store it in pickled form
        self.create_train_config(message["user_id"], self.get_user_public_key(message["user_id"]),
                                 message["user_signature"], session_key, message["route"], message["train_id"])
        client = docker.client.from_env()

        # login to the registry
        # login_result = client.login(username=os.getenv("TB_HARBOR_USER"), password=os.getenv("TB_HARBOR_PW"),
        #                             registry=self.registry_url)
        env_path = Path('.') / '.env'
        load_dotenv(dotenv_path=env_path)
        print(os.getenv("harbor_user"))
        print(os.getenv("harbor_user"))
        login_result = client.login(username=os.getenv("harbor_user"), password=os.getenv("harbor_pw"),
                                    registry=self.registry_url)
        self.create_temp_dockerfile(message, "train_config.json")
        image, logs = client.images.build(path=os.getcwd())
        repo = f"harbor.pht.medic.uni-tuebingen.de/pht_incoming/{message['train_id']}"
        image.tag(repo, tag="quick")
        # Remove files after image has been built successfully
        os.remove("train_config.json")
        shutil.rmtree("pht_train")
        result = client.images.push(repository=repo,
                                    tag="quick")
        print(result)
        # TODO remove image after pushing successfully
        return image

    def provide_hash(self, web_service_json):
        """
        Calculates the hash based on the user provided files and returns it for signing by the user
        :param web_service_json:
        :return:
        """
        session_id = self._generate_session_id()
        self.session_id = session_id
        files = self._get_files(web_service_json)
        self.generate_hash(web_service_json["user_id"], files, web_service_json["route"], session_id)
        return self.hash

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

    def create_train_config(self, user_id: str, user_pk: str, user_signature, session_key, route, train_id):
        """
        Creates a keyfile given the values provided by the webservice and stores it in the current working  directory
        :param user_id: id of the user creating the train
        :param user_pk: public key provided by the user bytes in PEM format
        :param user_signature: signature created with the offline tool using the users private key
        :return:
        """
        encrypted_session_key = self.encrypt_session_key(session_key, route)
        station_public_keys = self.get_station_public_keys(route)
        keys = {
            "user_id": user_id,
            "train_id": train_id,
            "session_id": b64encode(os.urandom(64)).decode(),
            "rsa_user_public_key": user_pk,
            "encrypted_key": encrypted_session_key,
            "rsa_public_keys": station_public_keys,
            "e_h": b64encode(self.hash).decode(),
            "e_h_sig": user_signature,
            "e_d": None,
            "e_d_sig": None,
            "digital_signature": None
        }
        with open("train_config.json", "w") as kf:
            json.dump(keys, kf, indent=2)

    def encrypt_session_key(self, session_key, route):
        """
        Encrypts the generated symmetric key with all public keys of the stations on the route
        :param session_key:
        :param route:
        :return:
        """
        station_public_keys = self.get_station_public_keys(route)
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
        vault_url = f"https://vault.pht.medic.uni-tuebingen.de/v1/station_pks/{station_id}"
        headers = {"X-Vault-Token": self.vault_token}
        r = requests.get(vault_url, headers=headers)
        data = r.json()["data"]
        return data["data"]["rsa_public_key"]

    def get_user_public_key(self, user_id):
        token = os.getenv("vault_token")
        vault_url = f"https://vault.pht.medic.uni-tuebingen.de/v1/user_pks/{user_id}"
        headers = {"X-Vault-Token": token}
        r = requests.get(vault_url, headers=headers)
        print(r.json())
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
        os.mkdir("pht_train")
        path = "pht_train"
        for endpoint in message["endpoints"]:
            endpoint_path = os.path.join(path, endpoint["name"])
            os.mkdir(endpoint_path)
            for command in endpoint["commands"]:
                command_path = os.path.join(endpoint_path, command["name"])
                os.mkdir(command_path)
                for file in command["files"]:
                    file_path = os.path.join(command_path, file[0])
                    with open(file_path, "w") as f:
                        f.write(file[1])

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
        hash = hashes.SHA512()
        hasher = hashes.Hash(hash, default_backend())
        hasher.update(user_id.encode())
        self.hash_files(hasher, files)
        hasher.update(bytes(route))
        hasher.update(session_id)
        digest = hasher.finalize()
        self.hash = digest
        return digest

    @staticmethod
    def hash_files(hasher: hashes.Hash, files: list):
        for file in files:
            hasher.update(file.encode())

    def _get_hash(self):
        if self.hash is not None:
            return self.hash
        else:
            print("No Hash available yet for the current train")


if __name__ == '__main__':
    tb = TrainBuilder("https://vault.lukaszimmermann.dev/v1/cubbyhole/station_public_keys")
    # keys = tb.get_station_public_keys([1, 2, 3])
    sym_key = Fernet.generate_key()
    route = [1, 2, 3]
    print(tb.encrypt_session_key(sym_key, route))
    json_message = create_json_message()
    tb.build_train(json_message)
    # tb.generate_pht_dir(json.loads(json_message))
    # keys = tb.create_key_file("123456", )
    # tb._save_key_file(keys)
