import pytest
from dotenv import load_dotenv, find_dotenv
from ..RabbitMqBuilder import RabbitMqBuilder
from train_lib.clients import PHTClient


@pytest.fixture
def tb_environment():
    pass

@pytest.fixture
def build_msg():
    pass


def test_initialization_and_setup():
    load_dotenv(find_dotenv())
    client = PHTClient(api_url="https://pht.tada5hi.net/api/pht/trains/")

    tb = RabbitMqBuilder(client)




