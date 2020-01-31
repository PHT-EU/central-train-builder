import docker
import pickle
import requests
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import json
import io


class TrainBuilder:
    def __init__(self, vault_url):
        # TODO perform docker login into harbour and check connection to vault, provide path to stored secrets
        # TODO maybe use a different class for vault/harbour clients
        # docker login
        self.vault_url = vault_url
        self.hash = None

    def build_train(self, web_service_json):
        """
        :param web_service_json: The message received from the
        :return: docker image of the final train
        """
        # TODO build docker image based on given values

        # Generate random number for session id, is this the right place?
        session_id = os.urandom(64)
        # self.hash = self.calculate_hash(user_id, algorithm, query, route, session_id)
        # # TODO how to use communation with the central service here ( async communication)
        #
        # # encrypt the query files before adding them to the image
        session_key = Fernet.generate_key()


        message = json.loads(web_service_json)
        fernet = Fernet(session_key)
        for file in message["query_files"]:
            self.encrypt_file(fernet, file)


        # create keyfile and store it in pickled form
        keys = self.create_key_file(message["user_id"], message["user_public_key"],
                                    message["user_signature"], session_key, message["route"])
        client = docker.client.from_env()
        self.create_temp_dockerfile("hello")

        return client.images.build(path=".")

    def create_temp_dockerfile(self, entrypoints, query_files):
        """

        :param endpoints: Dictionary created from message from webservice containing  all files defining the file
        structure of the train
        :return:
        """
        with open("Dockerfile", "w") as f:
            f.write("FROM harbor.lukaszimmermann.dev/pht_master/python:3.8.1-alpine3.11 \n")
            f.write("COPY entrypoint.py entrypoint.py\n")

    # TODO create keyfile as file, copy it to the image and delete it after

    def encrypt_file(self, fernet: Fernet, file):
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

    def create_key_file(self, user_id: str, user_pk: bytes, user_signature, session_key, route):
        """

        :param user_id: id of the user creating the train
        :param user_pk: public key provided by the user bytes in PEM format
        :param user_signature: signature created with the offline tool using the users private key
        :return: dictionary representing the key file used for validation
        """
        encrypted_session_key = self.encrypt_session_key(session_key, route)
        station_public_keys = self.get_station_public_keys(self.vault_url, route)
        keys = {
            "user_id": user_id,
            "session_id": os.urandom(64),
            "user_signature": user_signature,
            "rsa_user_public_key": user_pk,
            "encrypted_key": encrypted_session_key,
            "rsa_public_keys": station_public_keys,
            "e_h": None,
            "e_h_sig": None,
            "e_d": None,
            "e_d_sig": None,
            "digital_signature": None

        }
        return keys

    def _save_key_file(self, keys):
        with open("KeyFile", "wb") as kf:
            pickle.dump(keys, kf)

    def encrypt_session_key(self, session_key, route):
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
        vault_token = "s.endLK1VAnlkXsCRfUYjXlwlm"
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
    def _get_all_file_paths(message):
        """
        Parses the message received from the webservice and  returns  a list of all files to be hashed
        :param message:
        :return: list of files to be hashed
        """
        files = []
        for endpoint in message["endpoints"]:
            for command in endpoint["commands"]:
                files.append(command["files"])
        files.append(message["query_files"])

        return files

    def calculate_hash(self, user_id, files, route, session_id):
        """

        :param user_id: String value of the user id
        :param files: files to be hashed (algorithm and query files)
        :param route: route containing PIDs of stations included in the analysis
        :param session_id: session id randomly created by TB
        :return: hash value to be signed offline by user
        """
        # TODO  use json file from central webservice
        hash = hashes.SHA512()
        hasher = hashes.Hash(hash, default_backend())
        hasher.update(user_id.encode())
        self.hash_files(hasher, files)
        hasher.update(bytes(route))
        hasher.update(session_id)
        digest = hasher.finalize()
        # TODO make this function set the class value hash maybe
        return digest

    @staticmethod
    def hash_files(hasher: hashes.Hash, files: list):
        for file in files:
            with open(file, "rb") as f:
                hasher.update(file.read())

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

    tb.build_train([], [], route, "123456", "pk".encode(), "test_img", "user_sig")

    # keys = tb.create_key_file("123456", )
    # tb._save_key_file(keys)
