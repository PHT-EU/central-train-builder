[![Build and push image](https://github.com/PHT-Medic/central-train-builder/actions/workflows/CI.yml/badge.svg)](https://github.com/PHT-Medic/central-train-builder/actions/workflows/CI.yml)
[![CodeQL](https://github.com/PHT-Medic/central-train-builder/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/PHT-Medic/central-train-builder/actions/workflows/codeql-analysis.yml)
# TrainBuilder Service
This repository contains the TrainBuilder class responsible for building train Images according to a given schema,
adding these images to the pht/incoming harbor project and adding the associated to Vault storage

## Starting the service

Use the prebuilt [image](https://github.com/PHT-Medic/central-train-builder/pkgs/container/train-builder) to use the
service in a separate docker-compose file, the image uses the same environment variables as defined in the next section.

### docker-compose
1. Edit the environment variables in the `docker-compose.yaml` or in a `.env` in the working directory with the required values
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

2. Build the image and run the service: 
    ```
    docker-compose build
    docker-compose up -d
    ```


### Credits
[Icon](https://www.flaticon.com/authors/flat-icons)
