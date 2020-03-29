from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os
import requests
import json
import docker
import tempfile


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
    token = "s.jmMOV4W43R2zQ2WOuSQMwsV9"
    vault_url = f"https://vault.lukaszimmermann.dev/v1/station_pks/{user_id}"
    headers = {"X-Vault-Token": token}
    r = requests.get(vault_url, headers=headers)
    print(r.json())



def post_vault_key(user_id):
   """--header "X-Vault-Token: ..." \
    --request POST \
    --data @payload.json \
    https://127.0.0.1:8200/v1/secret/data/user_pks/3
   """

   token = "s.jmMOV4W43R2zQ2WOuSQMwsV9"
   vault_url = f"https://vault.lukaszimmermann.dev/v1/station_pks/{user_id}"
   headers = {"X-Vault-Token": token}
   pk = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0x7Fp8EyRbLQfhP1qtdL
rQqVtEaaChTlQLhcZM+drO0Xpf3oj7F1gb9VmTe9WIhY2NB2x9r5s41eiMPYpxHA
TJ6a0ba4mNT4pCX+RMWb6OPUqdLc6AHG2E1vhiwkXkQVdpBIRrzWJbyOmI6Sra1H
/Sny/6hTdS1YiJy0PUYpPUfPxbhGNPewebFRSNr/Dsx8OpKt1mZB/kXxDRZw/TIz
B0PYcokxqeHwqY00K7bgXNxbLr5REWUuqZhhbmtA6/z5wNXkWhdnvE6dyqFS4CQU
ttb1L3dWFTxbi6CqCaWcGYWC0/0jKOMpc1wfyYMw2h1wgGfCG1x6Ibq9Pre6gpQx
hQIDAQAB
-----END PUBLIC KEY-----
"""

   payload = {
       "options": {
           "cas": 0
       },
       "data":{
           "rsa_public_key" : pk,
       }
   }
   r = requests.post(vault_url, headers=headers, data=json.dumps(payload))
   print(r)

import io
if __name__ == '__main__':
    # generate_rsa_key_pair("D:\\train-builder\\keys", "user_3")
    # query_vault(2)
    # post_vault_key(3)
    client = docker.from_env()
    logs = client.images.build(path=os.getcwd())
    print(logs)

