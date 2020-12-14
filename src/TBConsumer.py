from train_lib.clients import Consumer, PHTClient
from train_lib.clients.rabbitmq import LOG_FORMAT
# from .TrainBuilder import TrainBuilder
import json
from dotenv import load_dotenv, find_dotenv
import os
import logging


class TBConsumer(Consumer):

    def __init__(self, amqp_url: str, queue: str = None):
        super().__init__(amqp_url, queue)
        # self.builder = TrainBuilder()
        self.pht_client = PHTClient(ampq_url=amqp_url, api_url=os.getenv("UI_TRAIN_API"))

    def on_message(self, _unused_channel, basic_deliver, properties, body):
        super().on_message(_unused_channel, basic_deliver, properties, body)

        message = json.loads(body)
        print(json.dumps(message, indent=2))

        # self._validate_token(message["token"])
        # self._process_message(message=message)

    def _process_message(self, message):
        pass

    def _validate_token(self, token):
        pass


def main():
    logging.basicConfig(level=logging.WARNING, format=LOG_FORMAT)
    AMPQ_URL = 'amqp://pht:start123@193.196.20.19:5672/'
    load_dotenv(find_dotenv())
    tb_consumer = TBConsumer(AMPQ_URL, "pht-main")
    tb_consumer.run()


if __name__ == '__main__':
    main()



