import json
import cryptography
import socketio

def create_json_message():

    """
    Generating a simluated message from the webservice also defining json structure for communication
    :return:
    """

    with open("/home/michaelgraf/Desktop/train-user-client/rsa_public_key", "rb") as f:
        user_pk = f.read()

    # TODO replace with signature based on hash files created with  the user private key
    user_signature = "user_signature"

    message = {
        # String containing USER ID
        "user_id": "123456",
        # String containing Train ID
        "train_id": "1",
        # String representation of user public key
        "user_public_key": user_pk.decode(),
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
                  # List of file paths associated with the command
                  "files": ["/home/michaelgraf/Desktop/trainTest/base-test/image_files/endpoints/calculate_sum"
                            "/commands/run/entrypoint.py",
                            "/home/michaelgraf/Desktop/trainTest/base-test/image_files/endpoints/calculate_sum"
                            "/commands/run/entrypoint.py",
                            "/home/michaelgraf/Desktop/trainTest/base-test/image_files/endpoints/calculate_sum"
                            "/commands/run/RESOURCES.tsv"]},
             ]},
            {"name": "hello_world",
             # List of dictionaries of commands (mostly only run for now)
             "commands": [
                 {"name": "run",
                  # List of file paths associated with the command
                  "files": ["/home/michaelgraf/Desktop/trainTest/base-test/image_files/endpoints/hello_world/commands"
                            "/run/entrypoint.py",
                            "/home/michaelgraf/Desktop/trainTest/base-test/image_files/endpoints/hello_world/commands"
                            "/run/README.md"]},
             ]},
        ],
        # List of file paths of query files passed to webservice
        "query_files": ["query1", "query2"],

    }
    return json.dumps(message, indent=4)

async def simulate_client():
    sio = socketio.AsyncClient()
    @sio.event
    async def connect():
        print("Connection established")

    @sio.event
    def my_message(data):
        print('message received with ', data)
        sio.emit('my response', {'response': 'my response'})

    @sio.event
    def disconnect():
        print('disconnected from server')

    await sio.connect('http://localhost:5000')
    print('my sid is', sio.sid)
    sio.wait()


if __name__ == '__main__':
    print(create_json_message())
