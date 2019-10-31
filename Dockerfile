FROM python:3.7.5-alpine3.10
COPY . /opt/srv
WORKDIR /opt/srv
RUN mkdir uploads && pip install -r --no-cache-dir requirements.txt && sync
ENTRYPOINT ["python", "app.py"]
