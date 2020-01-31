import json


def create_json_message():

    with open("/home/michaelgraf/Desktop/train-user-client/rsa_public_key", "rb") as f:
        user_pk = f.read()

    # TODO replace with signature based on hash files created with  the user private key
    user_signature = "user_signature"

    message = {
        "user_id": "123456",
        "user_public_key": user_pk.decode(),
        "user_signature": user_signature,
        "route": [1,2,3],
        # specify which of the provided master images to use
        "base_image": "harbor.lukaszimmermann.dev/pht_master/python:3.8.1-alpine3.11",
        # Path where all the files including the generated dockerfile will be stored
        "root_path": "/home/michaelgraf/Desktop/TrainBuilder/train-builder/tb_new",
        # Arbitrary length list of dictionaries of endpoints contained in train image
        "endpoints": [
            {"name": "calculate_sum",
             # List of dictionaries of commands (mostly only run for now)
             "commands": [
                 {"name": "run",
                  # List of file paths associated with the command
                  "files": []},
             ]},
            {"name": "collect_envvar",
             # List of dictionaries of commands (mostly only run for now)
             "commands": [
                 {"name": "run",
                  # List of file paths associated with the command
                  "files": []},
             ]},
            {"name": "hello_world",
             # List of dictionaries of commands (mostly only run for now)
             "commands": [
                 {"name": "run",
                  # List of file paths associated with the command
                  "files": []},
             ]},
        ],
        # List of file paths of query files passed to webservice
        "query_files": [],

    }
    return json.dumps(message, indent=4)


if __name__ == '__main__':
    print(create_json_message())
