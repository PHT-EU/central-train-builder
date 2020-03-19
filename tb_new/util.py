from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os


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



if __name__ == '__main__':
    generate_rsa_key_pair("/home/michael/pht/train-builder/keys", "station1")

    with open("/home/michael/pht/train-builder/keys/sk_station1", "rb") as sk:
        private_key = serialization.load_pem_private_key(sk.read(),
                                                         password=None,
                                                         backend=default_backend())

    with open("/home/michael/pht/train-builder/keys/pk_station1", "rb") as pk:
        public_key = serialization.load_pem_public_key(pk.read(), backend=default_backend())


    print(private_key)
    print(public_key)
