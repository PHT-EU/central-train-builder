import pika
from train_lib.clients import Consumer, PHTClient
from train_lib.clients.rabbitmq import LOG_FORMAT
import json
from dotenv import load_dotenv, find_dotenv
import os
import logging
from builder.TrainBuilder import TrainBuilder, BuildStatus
from loguru import logger

from builder.messages import BuilderResponse

LOGGER = logging.getLogger(__name__)


class TBConsumer(Consumer):

    def __init__(self, amqp_url: str, queue: str = "", routing_key: str = None):
        super().__init__(amqp_url, queue, routing_key=routing_key)
        self.ampq_url = amqp_url
        api_url = os.getenv("UI_TRAIN_API")
        if api_url[-1] != "/":
            api_url += "/"

        vault_url = os.getenv("VAULT_URL")
        if vault_url[-1] != "/":
            vault_url = vault_url + "/"

        self.pht_client = PHTClient(ampq_url=amqp_url, api_url=api_url,
                                    vault_url=vault_url, vault_token=os.getenv("VAULT_TOKEN"))

        self.builder = TrainBuilder()

        # Set auto reconnect to tr
        self.auto_reconnect = True
        # Configure routing key
        self.ROUTING_KEY = "tb"

    def on_message(self, _unused_channel, basic_deliver, properties, body):
        try:
            message = json.loads(body)
        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            response = BuilderResponse(type=BuildStatus.FAILED.value, data={"message": "Failed to parse message"})
            self.publish_events_for_train(response)
            super().on_message(_unused_channel, basic_deliver, properties, body)
            return
        logger.info(f"Received message: \n {message}")
        response = self.builder.process_message(message)

        print(response)
        # post message to train router to notify that the train has been built
        if response.type == BuildStatus.FINISHED.value:
            # check if the train has been already submitted if not notify the train router via rabbitmq
            if not self.builder.redis_store.train_submitted(response.data["id"]):
                self.post_message_for_train_router(response.data["id"])
        self.publish_events_for_train(response)
        super().on_message(_unused_channel, basic_deliver, properties, body)

    def publish_events_for_train(self, response: BuilderResponse, exchange: str = "pht",
                                 exchange_type: str = "topic", routing_key: str = "ui.tb.event"):

        connection = pika.BlockingConnection(pika.URLParameters(self.ampq_url))
        channel = connection.channel()
        channel.exchange_declare(exchange=exchange, exchange_type=exchange_type, durable=True)
        json_message = response.json().encode("utf-8")
        channel.basic_publish(exchange=exchange, routing_key=routing_key, body=json_message)
        logger.debug(f"Published message: {json_message}")
        connection.close()

    def post_message_for_train_router(self, train_id: str):
        """
        Notifies the train router via RabbitMQ that the train has been built and the route is stored in vault

        :param train_id: id of the train that has been built
        :return:
        """

        message = {
            "type": "trainBuilt",
            "data": {
                "id": train_id
            }
        }

        self.pht_client.publish_message_rabbit_mq(message, routing_key="tr")


def main():
    load_dotenv(find_dotenv())
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    tb_consumer = TBConsumer(os.getenv("AMQP_URL"), "", routing_key="tb")
    # os.getenv("UI_TRAIN_API")
    tb_consumer.run()


if __name__ == '__main__':
    main()
