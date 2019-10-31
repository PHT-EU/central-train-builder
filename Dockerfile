FROM python:3.7.5-alpine3.10
COPY . /opt/srv
WORKDIR /opt/srv
RUN mkdir -p uploads && pip install -r requirements.txt && sync
ENTRYPOINT ["python", "app.py"]
