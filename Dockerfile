FROM ubuntu
MAINTAINER michael.graf@uni-tuebingen.de
# update python version and replace python with python 3
RUN apt -y update && apt-get -y install software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa && apt -y update && apt -y install git
RUN apt-get install -y python3.8 && apt install python-is-python3 && apt install -y python3-pip

COPY requirements.txt /home/requirements.txt
RUN pip install -r /home/requirements.txt && mkdir /home/build_dir
RUN pip install git+https://gitlab.com/PersonalHealthTrain/implementations/germanmii/difuture/library/train-container-library.git
COPY ./src /home/src

# TODO add this for building from image
# curl -LO https://storage.googleapis.com/container-diff/latest/container-diff-linux-amd64 && \\
# chmod +x container-diff-linux-amd64 && sudo mv container-diff-linux-amd64 /usr/local/bin/container-diff


CMD ["python", "-u", "/home/src/TBConsumer.py"]
