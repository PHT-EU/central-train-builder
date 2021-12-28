import os

import pytest
from dotenv import load_dotenv, find_dotenv
from ..TrainBuilder import TrainBuilder
from train_lib.clients import PHTClient
from hvac import Client


@pytest.fixture
def tb_environment():
    pass

@pytest.fixture
def build_msg():
    pass

def test_get_service_token():
    load_dotenv(find_dotenv())
    client = PHTClient(api_url="https://pht.tada5hi.net/api/pht/trains/")
    tb = TrainBuilder(client)
    print(tb.vault_client)
    assert tb.service_key
    assert tb.client_id




def test_initialization_and_setup():
    load_dotenv(find_dotenv())
    client = PHTClient(api_url="https://pht.tada5hi.net/api/pht/trains/")

    tb = TrainBuilder(client)




