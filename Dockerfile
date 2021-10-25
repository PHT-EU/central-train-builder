FROM ubuntu
MAINTAINER michael.graf@uni-tuebingen.de
# update python version and replace python with python 3
RUN apt -y update && apt-get -y install software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && apt -y update && apt -y install git && \
    apt-get install -y python3.8 && apt install python-is-python3 && apt install -y python3-pip && \
    rm -rf /var/lib/apt/lists


COPY requirements.txt /home/requirements.txt
RUN pip install -r /home/requirements.txt && mkdir /home/build_dir
RUN pip install git+https://github.com/PHT-Medic/train-container-library.git
COPY ./src /home/src

CMD ["python", "-u", "/home/src/TBConsumer.py"]
