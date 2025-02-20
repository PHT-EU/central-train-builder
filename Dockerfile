FROM ubuntu
MAINTAINER michael.graf@uni-tuebingen.de
# update python version and replace python with python 3
RUN apt -y update && apt-get -y install software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && apt -y update && apt -y install git && \
    apt-get install -y python3.8 && apt install python-is-python3 && apt install -y python3-pip && \
    rm -rf /var/lib/apt/lists && \
    pip install pipenv

WORKDIR /opt/train-builder/

COPY Pipfile /opt/train-builder/Pipfile
COPY Pipfile.lock /opt/train-builder/Pipfile.lock

RUN pipenv install --system --deploy --ignore-pipfile
COPY . /home/src
RUN pip install /home/src

RUN pip install git+https://github.com/PHT-Medic/train-container-library.git


CMD ["python", "-u", "/home/src/TBConsumer.py"]
