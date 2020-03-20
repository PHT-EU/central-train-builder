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

    train_files = {}
    with open("D:\\train-builder\\test_train\\base-test-master\\image_files\\endpoints\\calculate_sum\\commands\\run\\entrypoint.py", "r") as f:
        train_files["entrypoint_1"] = f.read()
    with open("D:\\train-builder\\test_train\\base-test-master\\image_files\\endpoints\\calculate_sum\\commands\\run\\README.md", "r") as f:
        train_files["readme_1"] = f.read()
    with open("D:\\train-builder\\test_train\\base-test-master\\image_files\\endpoints\\calculate_sum\\commands\\run\\RESOURCES.tsv", "r") as f:
        train_files["resources_1"] = f.read()
    with open("D:\\train-builder\\test_train\\base-test-master\\image_files\\endpoints\\calculate_sum\\commands\\run\\QUERY.sql", "r") as f:
        train_files["query_1"] = f.read()
    with open("D:\\train-builder\\test_train\\base-test-master\\image_files\\endpoints\\hello_world\\commands\\run\\entrypoint.py", "r") as f:
        train_files["entrypoint_2"] = f.read()
    with open("D:\\train-builder\\test_train\\base-test-master\\image_files\\endpoints\\hello_world\\commands\\run\\README.md", "r") as f:
        train_files["readme_2"] = f.read()
    with open("D:\\train-builder\\test_train\\base-test-master\\image_files\\endpoints\\hello_world\\commands\\run\\QUERY.sql", "r") as f:
        train_files["query_2"] = f.read()




    message = {
        # String containing USER ID
        "user_id": "123456",
        # String containing Train ID
        "train_id": "1",
        # String representation of user public key
        # TODO move getting user public key to train builder
        # "user_public_key": user_pk.decode(),
        # Signature created with the offline tool.
        "user_signature": user_signature,
        "route": [1,2,3],
        # specify which of the provided master images to use
        "master_image": "harbor.lukaszimmermann.dev/pht_master/python:3.8.1-alpine3.11",
        # Path where all the files including the generated dockerfile will be stored
        "root_path": "/home/michaelgraf/Desktop/TrainBuilder/train-builder/tb_new",
        # Arbitrary length list of dictionaries of endpoints contained in train image
        "endpoints": [
            {"name": "calculate_sum",
             # List of dictionaries of commands (mostly only run for now)
             "commands": [
                 {"name": "run",
                  # List of list of files, consisting of filename and string representation of fileobject
                  "files": [["entrypoint.py", train_files["entrypoint_1"]], ["README.md", train_files["readme_1"]],
                            ["RESOURCES.tsv", train_files["resources_1"]], ["QUERY.sql", train_files["query_1"]]]}
             ]},
            {"name": "hello_world",
             # List of dictionaries of commands (mostly only run for now)
             "commands": [
                 {"name": "run",
                  # List of file paths associated with the command
                  "files": [["entrypoint.py", train_files["entrypoint_1"]], ["README.md", train_files["readme_2"]],
                            ["QUERY.sql", train_files["query_2"]]]}
             ]},
        ],

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
    def my_message(sid, data):
        print('message received with ', data)
        sio.emit('my_response', {'response': 'my response'})

    @sio.event
    def disconnect():
        print('disconnected from server')

    await sio.connect('http://localhost:8888')
    print('my sid is', sio.sid)
    await sio.emit("my_message", {"foo": 123565})

    await sio.wait()



if __name__ == '__main__':
    print(create_json_message())
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(simulate_client())
