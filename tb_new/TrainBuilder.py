import docker
import pickle
import requests
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import json
import socketio

from simulate_webservice import create_json_message


class TrainBuilder:
    def __init__(self, vault_url):
        # TODO perform docker login into harbour and check connection to vault, provide path to stored secrets
        # TODO maybe use a different class for vault/harbour clients
        # docker login
        self.vault_url = vault_url
        self.hash = None
        self.registry_url = "harbor.lukaszimmermann.dev"

    def build_train(self, web_service_json, user_signature):
        """
        :param web_service_json: The message received from the
        :return: docker image of the final train
        """
        # TODO build docker image based on given values

        # Generate random number for session id, is this the right place?
        session_id = os.urandom(64)
        hash = self.provide_hash(web_service_json, session_id)
        # # TODO how communicate with the central service here ( async communication)
        # TODO need to wait for user to provide the signed hash before creating the keyfile etc
        # # encrypt the query files before adding them to the image
        session_key = Fernet.generate_key()

        message = json.loads(web_service_json)

        fernet = Fernet(session_key)
        for file in message["query_files"]:
            self.encrypt_file(fernet, file)

        # create keyfile and store it in pickled form
        self.create_key_file(message["user_id"], message["user_public_key"],
                             message["user_signature"], session_key, message["route"], message["train_id"])
        client = docker.client.from_env()
        self.create_temp_dockerfile(message, "KeyFile")
        image = client.images.build(path=".", tag=message["train_id"])
        # Remove KeyFile after image has been built successfully
        os.remove("KeyFile")
        # TODO also remove other files
        self.push_train(message["train_id"], client, message["route"][0])

        # TODO remove image after pushing successfully

        return image

    def provide_hash(self, web_service_json, session_id):
        """
        Calculates the hash based on the user provided files and returns it for signing by the user
        :param web_service_json:
        :return:
        """
        files = self._get_files(web_service_json)
        self.generate_hash(web_service_json["user_id"], files, web_service_json["route"], session_id)
        return self.hash

    def push_train(self, tag, client, first_station):
        # TODO load registry auth stuff from dockerconfig?
        try:
            client.login("username", "password", "email", self.registry_url, reauth=True)
        except docker.errors.APIError:
            print("Something went wrong logging in, check docker config etc")
            # TODO sensibly handle error

        # TODO check if this works
        client.images.push(repository="harbor.likaszimmermann.dev" + "/" + first_station, tag=tag)

    def create_temp_dockerfile(self, web_service_json, key_file_path):
        """
        Creates a dockerfile to build a train image
        :param endpoints: Dictionary created from message from webservice containing  all files defining the file
        structure of the train
        :return:
        """
        with open("Dockerfile", "w") as f:
            f.write("FROM " + web_service_json["master_image"] + "\n")
            file_paths = self._generate_file_paths(web_service_json)
            for file in file_paths:
                f.write("COPY " + file[0] + " " + file[1] + "\n")
            f.write("COPY " + key_file_path + " " + os.path.join("/opt/pht_train/", "KeyFile"))

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

    def create_key_file(self, user_id: str, user_pk: str, user_signature, session_key, route, train_id):
        """
        Creates a keyfile given the values provided by the webservice and stores it in the current working  directory
        :param user_id: id of the user creating the train
        :param user_pk: public key provided by the user bytes in PEM format
        :param user_signature: signature created with the offline tool using the users private key
        :return:
        """
        encrypted_session_key = self.encrypt_session_key(session_key, route)
        station_public_keys = self.get_station_public_keys(self.vault_url, route)
        keys = {
            "user_id": user_id,
            "train_id": train_id,
            "session_id": os.urandom(64),
            "rsa_user_public_key": user_pk.encode(),
            "encrypted_key": encrypted_session_key,
            "rsa_public_keys": station_public_keys,
            "e_h": self.hash,
            "e_h_sig": user_signature,
            "e_d": None,
            "e_d_sig": None,
            "digital_signature": None

        }
        with open("KeyFile", "wb") as kf:
            pickle.dump(keys, kf)

    def encrypt_session_key(self, session_key, route):
        """
        Encrypts the generated symmetric key with all public keys of the stations on the route
        :param session_key:
        :param route:
        :return:
        """
        station_public_keys = self.get_station_public_keys(self.vault_url, route)
        encrpyted_session_key = {}
        for id, key in station_public_keys.items():
            pk = self.load_public_key(key)
            encrypted_key = pk.encrypt(session_key,
                                       padding.OAEP(
                                           mgf=padding.MGF1(algorithm=hashes.SHA512()),
                                           algorithm=hashes.SHA512(),
                                           label=None
                                       ))
            encrpyted_session_key[id] = encrypted_key

        return encrpyted_session_key

    def upload_user_public_key(self, user_pk):
        # TODO upload the provided user pk to vault?
        # TODO is this really necessary??? Maybe doesnt need to be stored
        pass

    @staticmethod
    def get_station_public_keys(vault_url: str, route: list):
        """
        Gets the public keys of the stations included in the route from the vault service
        :param vault_url: location of key storage
        :param route: route containing PID of stations
        :return: dictionary with statino PIDs as keys and the associated public keys as values
        """
        # TODO replace with secure token
        vault_token = ""
        headers = {"X-Vault-Token": vault_token}
        r = requests.get(vault_url, headers=headers)
        keys: dict = r.json()["data"]
        public_keys = {}
        for key in keys:
            if int(key.split("_")[1]) in route:
                public_keys[int(key.split("_")[1])] = keys[key].encode()

        return public_keys

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
    def _get_files(message):
        """
        Gets the paths (on the server) of all specified files
        :param message: json message received from the webserver
        :return: list of file paths of relevant files
        """
        files = []
        for endpoint in message["enpoints"]:
            for command in endpoint["commands"]:
                for f in command["files"]:
                    files.append(f)
        files.append(message["query_files"])

        return files


    @staticmethod
    def _generate_file_paths(message):
        """
        Parses the message received from the webservice and  returns  a list of all files to be hashed
        :param message:
        :return: list of files to be hashed
        """
        files = []
        query_prefix = "/opt/pht_train/executions/_currently_running/_working"
        endpoint_prefix = "/opt/pht_train/endpoints"
        for endpoint in message["endpoints"]:
            path = os.path.join(endpoint_prefix, endpoint["name"])
            for command in endpoint["commands"]:
                path = os.path.join(path, command["name"])
                for file in command["files"]:
                    file_path = os.path.join(path, file)
                    files.append((file, file_path))

        for query_file in message["query_files"]:
            files.append((query_file, os.path.join(query_prefix, query_file)))
        return files

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
            with open(file, "rb") as f:
                hasher.update(f.read())

    def _get_hash(self):
        if self.hash is not None:
            return self.hash
        else:
            print("No Hash available yet for the current train")
            



if __name__ == '__main__':
    tb = TrainBuilder("https://vault.lukaszimmermann.dev/v1/cubbyhole/station_public_keys")
    # keys = tb.get_station_public_keys("https://vault.lukaszimmermann.dev/v1/cubbyhole/station_public_keys", [1, 2, 3])
    sym_key = Fernet.generate_key()
    route = [1, 2, 3]
    print(tb.encrypt_session_key(sym_key, route))
    json_message = create_json_message()
    tb.build_train(json_message)

    # keys = tb.create_key_file("123456", )
    # tb._save_key_file(keys)
