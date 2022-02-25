[![Build and push image](https://github.com/PHT-Medic/central-train-builder/actions/workflows/CI.yml/badge.svg)](https://github.com/PHT-Medic/central-train-builder/actions/workflows/CI.yml)
[![CodeQL](https://github.com/PHT-Medic/central-train-builder/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/PHT-Medic/central-train-builder/actions/workflows/codeql-analysis.yml)
[![Vulnerability Scan](https://github.com/PHT-Medic/central-train-builder/actions/workflows/image_scan.yml/badge.svg)](https://github.com/PHT-Medic/central-train-builder/actions/workflows/image_scan.yml)
[![codecov](https://codecov.io/gh/PHT-Medic/central-train-builder/branch/master/graph/badge.svg?token=B3QQACAM7K)](https://codecov.io/gh/PHT-Medic/central-train-builder)
# TrainBuilder Service
This repository contains the TrainBuilder class responsible for building valid train images based on the configuration 
selected in the user interface, as well as the train algorithm files submitted to the UI.
Based on the configuration the service obtains the files from the central API and the public keys of both the 
participating stations and the user who created the train from our vault secret storage.  
Using these values the train builder creates the `train_config.json` containing all relevant information about the train
and packages it along with the user submitted files into a train image.  
The selected route is then submitted to vault under the given train ID and the image is pushed to the `pht_incoming`
project of our container registry.

## Environment variables

The service is configured using environment variables, which define the connection parameters to other central PHT services.
The following environment variables are required:
```
   VAULT_TOKEN=<token>
   VAULT_URL=https://vault-pht-dev.tada5hi.net
   HARBOR_API=https://harbor-pht.tada5hi.net/api/v2.0
   HARBOR_URL=https://harbor-pht.tada5hi.net
   HARBOR_USER=<harbor_user>
   HARBOR_PW=<harbor_pw>
   AMPQ_URL=<ampq_url>
   UI_TRAIN_API=https://pht-dev.tada5hi.net/api/trains/
   REDIS_HOST=redis
 ```
## Starting the service

Use the prebuilt [image](https://github.com/PHT-Medic/central-train-builder/pkgs/container/train-builder) to use the
service in a separate docker-compose file, the image uses the same environment variables as defined in the next section.

### docker-compose
1. Edit the environment variables in the `docker-compose.yaml` or in a `.env` in the working directory with the required values
2. Build the image and run the service: 
    ```
    docker-compose build
    docker-compose up -d
    ```


### Credits
[Icon](https://www.flaticon.com/authors/flat-icons)
