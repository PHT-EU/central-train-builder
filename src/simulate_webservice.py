import json
import cryptography
import socketio
import asyncio
import os

def create_json_message():

    """
    Generating a simluated message from the webservice also defining json structure for communication
    :return:
    """

    #with open("/home/michaelgraf/Desktop/train-user-client/rsa_public_key", "rb") as f:
    #    user_pk = f.read()

    # TODO replace with signature based on hash files created with  the user private key
    user_signature = "user_signature"

    with open("./entrypoint.py", "r") as f:
        minimal_example = f.read()
        """
        schema in PHT-UI
        # data.action
        # data.data
        if data.action == 'build':

            data.data 

                type: train.type, #string: one of "analyse","discovery"
                train_id: train.id, #int
                user_id: train.user_id, #int
                user_public_key: train.public_key, #string
                user_signature: train.signed_hash, #string
                route: stationIds, # int array
                master_image: train.master_image, #string
                endpoint: {
                    name: 'default',
                    command: 'run',
                    files: [{name: "file_name", content:"inhalt"}] 
                }

   # old

    message = {
        # String containing USER ID
        "user_id": 2,
        # String containing Train ID
        "train_id": 1,
        # String representation of user public key
        # TODO move getting user public key to train builder
        # "user_public_key": user_pk.decode(),
        # Signature created with the offline tool.
        "user_signature": user_signature,
        "route": [1,2,3],
        # specify which of the provided master images to use
        "master_image": "harbor.pht.medic.uni-tuebingen.de/pht_master/python_train:master",
        # Path where all the files including the generated dockerfile will be stored
        "root_path": "/home/ubuntu/repos/train-builder/",
        # Arbitrary length list of dictionaries of endpoints contained in train image
        "endpoints": [
            {
                "name": "encryption",
                "commands": [
                    {
                        "name": "run",
                        "files": [["entrypoint.py", entrypoint_hiv]]
                    }
                ]
            },
            {
                "name": "hiv",
                "commands": [
                    {
                        "name": "run",
                        "files": [["entrypoint.py", entrypoint_hiv]]
                    }
                ]
            },
        ]

    }
    """
        message = {
            # String containing USER ID
            "user_id": 2,
            # String containing Train ID
            "train_id": 1,
            # String representation of user public key
            # TODO move getting user public key to train builder
            # "user_public_key": user_pk.decode(),
            # Signature created with the offline tool.
            "user_signature": user_signature,
            "route": [1, 2, 3],
            # specify which of the provided master images to use
            "master_image": "harbor.pht.medic.uni-tuebingen.de/pht_master/python_train:master",
            # Path where all the files including the generated dockerfile will be stored
            "root_path": "/home/ubuntu/repos/train-builder/",
            # Arbitrary length list of dictionaries of endpoints contained in train image
            "endpoints": [
                {
                    "name": "encryption",
                    "commands": [
                        {
                            "name": "run",
                            "files": [["entrypoint.py", minimal_example]]
                        }
                    ]
                }
            ]

        }
    with open("sample_message_new.json", "w") as f:
        json.dump(message, f, indent=2)
    return json.dumps(message, indent=2)


async def simulate_client():
    sio = socketio.AsyncClient()
    @sio.event
    async def connect():
        print("Connection established")

    @sio.event
    async def my_message(sid, data):
        print('message received with ', data)
        sio.emit('my_response', {'response': 'my response'})

    @sio.on("generated_hash")
    async def received(data):
        print("Generated hash")
        print(data)

    @sio.on("train")
    async def built_train(data):
        print("Train successfully built")
        print(data)

    @sio.on("build_failure")
    async def print_error(data):
        print(data)

    @sio.event
    def disconnect():
        print('disconnected from server')

    await sio.connect('http://localhost:3002')
    print('my sid is', sio.sid)
    await sio.emit("my_message", {"foo": 123565})

    # await sio.emit("generate_hash", data=create_json_message())
    # await sio.emit("build_minimal_example", data=create_json_message())

    await sio.wait()

if __name__ == '__main__':
    sio = socketio.Client()

    @sio.event
    def connect():
        print("I'm connected!")

    sio.connect('http://localhost:7777')

    minimal_example_message = "../test_message.json"
    file_size_message = "../test_message_encryption_test.json"
    with open(file_size_message, "r") as f:
        msg = json.load(f)

    with open("../test/test_train/entrypoint.py", "r") as tf:
        msg["data"]["endpoint"]["files"][0]["content"] = tf.read()
    print(msg)
    sio.emit("train", msg)

    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(simulate_client())
