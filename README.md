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
    - UI_TRAIN_API=http://pht-ui.personalhealthtrain.de/api/pht/trains/
    - AMPQ_URL=<ampq_url>
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

### Credits
[Icon](https://www.flaticon.com/authors/flat-icons)
