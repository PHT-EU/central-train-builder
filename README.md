# TrainBuilder Service
This repository contains the TrainBuilder class responsible for building train Images according to a given schema,
adding these images to the pht/incoming harbor project and adding the associated to Vault storage

## Starting the service

### docker-compose 
1. Edit the environment variables in the `docker-compose.yaml` file with the required values
    ```
    - vault_token=<vault_token>
    - vault_url=https://vault.pht.medic.uni-tuebingen.de/
    - harbor_url=https://harbor.personalhealthtrain.de
    - harbor_user=<harbor_user>
    - harbor_pw=<harbor_pw>
    - build_dir=/home/build_dir
    - tb_dir=/home
    ```

2. Build the image and run the services: 
    ```
    docker-compose build
    docker-compose up
    ```
   
### system service



## Installation
This package requires docker to be installed on the host machine.  
The required python 3 packages can be installed via  `pip install -r requirements.txt`
Make sure there is a redis instance running and available on `localhost:6379`

### container-diff
Install the [container-diff](https://github.com/GoogleContainerTools/container-diff) tool and add it to path
```
curl -LO https://storage.googleapis.com/container-diff/latest/container-diff-linux-amd64 && chmod +x container-diff-linux-amd64 && sudo mv container-diff-linux-amd64 /usr/local/bin/container-diff
```

## Testing
In the test directory run 
`docker build -t harbor.personalhealthtrain.de/pht_train_submission/test -f Dockerfile_test .` to build an invalid image




## Configuration/Authentification
To access harbor and vault, username and password or an authentification token are respectively required. These are read
by the TrainBuilder from a `.env` file in the projects root directory.
The addresses of the vault and harbor instances are currently hardcoded.  
```
harbor_user=<user>
harbor_pw=<pw>
harbor_url=https://harbor.pht.medic.uni-tuebingen.de/pht_incoming
vault_token=<token>
vault_url=https://vault.pht.medic.uni-tuebingen.de/v1

```

## CLI
To build minimal examples one can use the command line interface as such:
```
$ python tb_cli.py --entrypoint <path to entrypoint> --train_name <name of train> --route 1,2,3,4
```
This will build a docker image that, once run will execute `python entrypoint.py`

## Async webservice
To run the train builder as a asynchronous webservice using socket-io
use the command:
 ```
python TrainBuilderService.py  
```
This will run a socket-io server listening for events under `127.0.0.1:7777`. This service is currently processing two
types of events:
1. **generate_hash**: which processes a message of the type defined in the sample_message.json file and generate a hash
for the user to sign
2. **build_train**: processes the same message but this time including the user signed signature of the provided hash,
this will create the train_config.json (example under same name) containing relevant security information, build the
docker image, post the route to vault and upload the docker image to harbor