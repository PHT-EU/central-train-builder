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

    with open("D:\\demo-hiv-uc\\train\\dev_train\\endpoints\\encryption_train\\commands\\run\\entrypoint.py", "r") as f:
        entrypoint_encryption = f.read()
    with open("D:\\demo-hiv-uc\\train\\dev_train\\endpoints\\hiv_train\\commands\\run\\entrypoint.py", "r") as f:
        entrypoint_hiv = f.read()

    message = {
        # String containing USER ID
        "user_id": "2",
        # String containing Train ID
        "train_id": "1",
        # String representation of user public key
        # TODO move getting user public key to train builder
        # "user_public_key": user_pk.decode(),
        # Signature created with the offline tool.
        "user_signature": user_signature,
        "route": [1,2,3],
        # specify which of the provided master images to use
        "master_image": "harbor.pht.medic.uni-tuebingen.de/pht_master/python_train:master",
        # Path where all the files including the generated dockerfile will be stored
        "root_path": "/home/michaelgraf/Desktop/TrainBuilder/train-builder/tb_new",
        # Arbitrary length list of dictionaries of endpoints contained in train image
        "endpoints": [
            {
                "name": "encryption",
                "commands": [
                    {
                        "name": "run",
                        "files": [["entrypoint.py", entrypoint_encryption]]
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
    with open("sample_message.json", "w") as f:
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

    @sio.on("built_train")
    async def built_train(data):
        print("Train successfully built")

    @sio.on("build_failure")
    async def print_error(data):
        print(data)

    @sio.event
    def disconnect():
        print('disconnected from server')

    await sio.connect('http://localhost:7777')
    print('my sid is', sio.sid)
    await sio.emit("my_message", {"foo": 123565})

    await sio.emit("generate_hash", data=create_json_message())
    await sio.emit("build_train", data=create_json_message())

    await sio.wait()

if __name__ == '__main__':
    print(create_json_message())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(simulate_client())
