from train_lib.clients import Consumer, PHTClient
from train_lib.clients.rabbitmq import LOG_FORMAT
# from .TrainBuilder import TrainBuilder
import json
from dotenv import load_dotenv, find_dotenv
import os
import logging
import jwt
from RabbitMqBuilder import RabbitMqBuilder

LOGGER = logging.getLogger(__name__)


class TBConsumer(Consumer):

    def __init__(self, amqp_url: str, queue: str = None, public_key_path: str = None, routing_key: str = None):
        super().__init__(amqp_url, queue, routing_key=routing_key)
        load_dotenv(find_dotenv())
        # self.builder = TrainBuilder()
        self.pht_client = PHTClient(ampq_url=amqp_url, api_url=os.getenv("UI_TRAIN_API"),
                                    vault_url=os.getenv("vault_url"), vault_token=os.getenv("vault_token"))
        self.builder = RabbitMqBuilder(self.pht_client)

        if public_key_path:
            with open(public_key_path, "r") as public_key_file:
                self.pk = public_key_file.read()

        # Set auto reconnect to true
        self.auto_reconnect = True
        # Configure routing key
        self.ROUTING_KEY = "tb"

    def on_message(self, _unused_channel, basic_deliver, properties, body):
        try:
            message = json.loads(body)
            # print(json.dumps(message, indent=2))
        except:
            self.pht_client.publish_message_rabbit_mq(
                {"type": "trainBuildFailed", "data": {"message": "Malformed JSON"}},
                routing_key="ui")
            super().on_message(_unused_channel, basic_deliver, properties, body)
            return
        LOGGER.info(f"Received message: \n {message}")
        action, data, meta_data = self._process_message(message)
        if action == "trainBuild":
            LOGGER.info("Received build command")

            code, build_message = self.builder.build_train(data, meta_data)
            response = self._make_response(message, code, build_message)

        else:
            LOGGER.warning(f"Received unrecognized action type - {action}")
            response = self._make_response(message, 1, f"Unrecognized action type: {action}")

        self.pht_client.publish_message_rabbit_mq(response, routing_key="ui.tb")
        super().on_message(_unused_channel, basic_deliver, properties, body)


    @staticmethod
    def _process_message(message):
        data = message["data"]
        meta_data = message["metadata"]
        action = message["type"]
        return action, data, meta_data

    @staticmethod
    def _make_response(message, code, build_message):
        if code == 0:
            message["type"] = "trainBuilt"
        else:
            message["type"] = "trainBuildFailed"
        message["data"]["buildMessage"] = build_message

        return message


def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    tb_consumer = TBConsumer(os.getenv("AMPQ_URL"), "", routing_key="tb")
    tb_consumer.run()


if __name__ == '__main__':
    main()
