from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os
import requests
import json
import docker
import tempfile
from dotenv import load_dotenv


def generate_rsa_key_pair(dir, id):
    """
    Generates and rsa private/public key pair and stores it in the given dir name after id
    :param dir: directory to store keys in
    :param id: name of the key
    :return:
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    public_key = private_key.public_key()

    sk_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                       format=serialization.PrivateFormat.TraditionalOpenSSL,
                                       encryption_algorithm=serialization.NoEncryption())
    pk_pem = public_key.public_bytes(encoding=serialization.Encoding.PEM,
                                     format=serialization.PublicFormat.SubjectPublicKeyInfo)

    with open(os.path.join(dir, f"sk_{id}"), "wb") as sk_file:
        sk_file.write(sk_pem)

    with open(os.path.join(dir, f"pk_{id}"), "wb") as pk_file:
        pk_file.write(pk_pem)


def query_vault(user_id):
    token = os.getenv("vault_token")
    url = os.getenv("vault_url")
    vault_url = f"{url}/user_pks/{user_id}"
    headers = {"X-Vault-Token": token}
    r = requests.get(vault_url, headers=headers)
    print(json.dumps(r.json(), indent=2))


def post_route_to_vault(name, route):
    """--header "X-Vault-Token: ..." \
    --request POST \
    --data @payload.json \
    https://127.0.0.1:8200/v1/secret/data/user_pks/3
   """

    token = os.getenv("vault_token")
    url = os.getenv("vault_url")
    vault_url = f"{url}/kv-pht-routes/data/{name}"
    headers = {"X-Vault-Token": token}

    payload = {
        "options": {
            "cas": 0
        },
        "data": {
            "harborProjects": route,
            "repositorySuffix": "busybox"
        }
    }
    try:
        # TODO catch update of same route
        r = requests.post(vault_url, headers=headers, data=json.dumps(payload))
        print(r.json())
    except Exception as e:
        print(e)



if __name__ == '__main__':
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path)
    # generate_rsa_key_pair("D:\\train-builder\\keys", "user_3")
    query_vault(2)
    # post_vault_key(3)
    # client = docker.from_env()
    # logs = client.images.build(path=os.getcwd())
    # print(logs)
