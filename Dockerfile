FROM python:3.9-slim-buster
COPY requirements.txt /home/requirements.txt
RUN pip install -r /home/requirements.txt && mkdir /home/build_dir \
    && pip install git+https://gitlab.com/PersonalHealthTrain/implementations/germanmii/difuture/train-container-library.git
COPY ./src /home/src
COPY rsa.public /home/rsa.public

COPY TrainBuilderService.py /home/TrainBuilderService.py
    # TODO add this for building from image

    # curl -LO https://storage.googleapis.com/container-diff/latest/container-diff-linux-amd64 && \\
    # chmod +x container-diff-linux-amd64 && sudo mv container-diff-linux-amd64 /usr/local/bin/container-diff


CMD ["python", "-u", "/home/TrainBuilderService.py"]
