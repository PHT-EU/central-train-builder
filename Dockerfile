FROM python:3.9-slim-buster
COPY ./src /home/src
COPY rsa.public /home/rsa.public
COPY requirements.txt /home/requirements.txt
COPY TrainBuilderService.py /home/TrainBuilderService.py

RUN pip install -r /home/requirements.txt && mkdir /home/build_dir
    # curl -LO https://storage.googleapis.com/container-diff/latest/container-diff-linux-amd64 && \\
    # chmod +x container-diff-linux-amd64 && sudo mv container-diff-linux-amd64 /usr/local/bin/container-diff


CMD ["python", "-u", "/home/TrainBuilderService.py"]
