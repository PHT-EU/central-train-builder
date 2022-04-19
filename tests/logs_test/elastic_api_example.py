import time

from elasticsearch import Elasticsearch
from dotenv import load_dotenv, find_dotenv
import os, json, logging
from loguru import logger
from datetime import datetime
from train_schema import Train
from elasticapm.handlers.logging import Formatter
import ecs_logging

load_dotenv(find_dotenv())

api_key = os.getenv('ELASTIC_API_KEY')
elastic_host = "http://localhost:9200"
index = "train_logs_test"
tag_tuebingen = ["train_tuebingen"]
tag_munich = ["train_munich"]
tag_aachen = ["train_aachen"]

search_query_all = {
    "match_all": {}
}

def get_search_query_tag(tag: str):
    return {
        "bool": {
            "must": [
                {
                    "term": {
                        "tags": {
                            "value": f"{tag}"
                        }
                    }
                }
            ]
        }
    }

_id = 1

train_tuebingen = Train(id=10, name="Train Tuebingen", created_at=datetime.now(), is_active=True)
train_munich = Train(id=100, name="Train Munich", created_at=datetime.now(), is_active=True)
train_aachen = Train(id=1000, name="Train Aachen", created_at=datetime.now(), is_active=True)

def create_example_logs(obj_in: Train, storage_path: str):
    log = logging.getLogger()
    fh = logging.FileHandler(storage_path)
    formatter = ecs_logging.StdlibFormatter()
    fh.setFormatter(formatter)
    logger_id = logger.add(fh, format="{message}")


    logger.info(f"Train with id : {obj_in.id} and name : {obj_in.name} got build at timestamp : {obj_in.created_at}")
    logger.info(f"Initializing docker client and logging into registry")
    logger.info("Login result -- Login Succeeded")
    logger.warning("Initializing vault client & store")
    logger.warning("Vault client initialized")
    logger.warning("Requesting service credentials from vault")
    logger.debug("Service token obtained")
    logger.debug("Connecting to redis")
    logger.debug("Redis connection established. Setting up store...")
    logger.info("Redis store initialized")
    logger.info("Validating setup")
    logger.info("Setup complete")

    logger.remove(logger_id)

create_example_logs(train_tuebingen, "example_logs/tuebingen_example_train.log")
create_example_logs(train_munich, "example_logs/munich_example_train.log")
create_example_logs(train_aachen, "example_logs/aachen_example_train.log")

logger.info("Example logs for 3 different Trains have been created.")



#Creating connection to Elasticsearch host
elastic_client = Elasticsearch(hosts=elastic_host, api_key=("elastic", api_key))
logger.info("Connection to Elasticsearch got created")

def post_logs_to_index(index: str, tag: list, path: str):

    global _id

    with open(path, 'r') as logs:
        logs = logs.readlines()

    for log in logs:
        log = json.loads(log)
        log['tags'] = tag
        #print("Line in logs : {}".format(log))
        post = elastic_client.index(index=index, id=_id, document=log)
        _id += 1
        #print(post)

post_logs_to_index(index, tag_tuebingen, "example_logs/tuebingen_example_train.log")
post_logs_to_index(index, tag_munich, "example_logs/munich_example_train.log")
post_logs_to_index(index, tag_aachen, "example_logs/aachen_example_train.log")

logger.info(f"Example logs for 3 different trains have been created at {elastic_host} with index : {index}")
time.sleep(5)

def get_logs_by_id(index: str, id: int):

    return elastic_client.get(index=index, id=id)

log_tuebingen_id = get_logs_by_id(index, 10)
log_munich_id = get_logs_by_id(index, 20)
log_aachen_id = get_logs_by_id(index, 30)

logger.info(f"Log with id 10 has been retrieved : {log_tuebingen_id}")
logger.info(f"Log with id 20 has been retrieved : {log_munich_id}")
logger.info(f"Log with id 30 has been retrieved : {log_aachen_id}")

def get_logs_by_query(index: str, query: dict):

    return elastic_client.search(index=index, query=query)

log_query_all = get_logs_by_query(index, search_query_all)

logger.info(f"All results matching the index : {index} have been retrieved : {log_query_all}")


log_tuebingen_query = get_logs_by_query(index, get_search_query_tag(tag_tuebingen[0]))
log_munich_query = get_logs_by_query(index, get_search_query_tag(tag_munich[0]))
log_aachen_query = get_logs_by_query(index, get_search_query_tag(tag_aachen[0]))

def print_log_retrievals(search_response: dict):

    print("Got %d Hits:" % search_response['hits']['total']['value'])
    for hit in search_response['hits']['hits']:
        print("%(@timestamp)s %(message)s" % hit["_source"])

logger.info(f"Logs with tag {tag_tuebingen} has been retrieved.")
print_log_retrievals(log_tuebingen_query)
logger.info(f"Logs with tag {tag_munich} has been retrieved.")
print_log_retrievals(log_munich_query)
logger.info(f"Logs with tag {tag_aachen} has been retrieved.")
print_log_retrievals(log_aachen_query)



