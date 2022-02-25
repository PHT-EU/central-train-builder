import json
import pytest
from builder.messages import BuildMessage


@pytest.fixture
def build_message():
    return {
        "id": "f54f58d9-58a1-4141-9dfb-a48b2a275998",
        "type": "trainBuildStart",
        "metadata": {},
        "data": {
            "user_id": 5,
            "user_rsa_secret_id": "test-rsa",
            "userPaillierSecretId": "test-paillier",
            "id": "da8fd868-0fed-42e3-b6d8-5abbf0864d4a",
            "proposal_id": 4,
            "stations": [
                "1"
            ],
            "files": [
                "test_train/entrypoint.py",
                "test_train/requirements.txt"
            ],
            "master_image": "python/slim",
            "entrypointExecutable": "python",
            "entrypoint_path": "test_train/entrypoint.py",
            "session_id": "8203c4facff907d3bd83f8399e9a97aa4270e27acb4369f5bcdaab20643f2dc7c2ca8fe78a576c3ae7ac56b64d89a778aa86f7f90360734965dce0264ddcd705",
            "hash": "91416369e845e7ff12efe8514736d468b71bfc15cc5ded92399a1a558f4317da68cfd5884cb9e5bbbac15ce45731afe4e47ced256c7a2e493ff7fad5481b8d31",
            "hash_signed": "ace71ecae217b8da4426cee8ba8abeddab6d1d9c9d073e7c54197b82a1d453189ca2a3e278be7747b4e0fac28bba32dc1b5a4dbc4b060a2f5e659180367b56b90b6ee8f59f529206e39645acd0bd24c03c3ef291ac8ad91dbf4390541033656ec3ee48a516a94348cb60ed596be305c3754e7e4b66dc433bb47a2483ea7d772cc6a353bb43b82e4f35f7dc6ee1f502765d64785ea816b20eed6c3a1ea857a753d5048e16d395d3479b62d91c9870d9f19ee0740b6051a3089e5350227820281406d267e188ac4edb1f0f3ebd36a0aa6cb2eeeaaa71023b0e8e6381d3bc683277208a7c91de77d61e4a8ca8f71621449e564f57bb8eaef25f08da61e8b0b79f61",
            "user_he_key": "12345241",
            "entrypoint_command": "run"
        }
    }


@pytest.fixture
def build_message_query():
    return {
        "id": "f54f58d9-58a1-4141-9dfb-a48b2a275998",
        "type": "trainBuildStart",
        "metadata": {},
        "data": {
            "user_id": 5,
            "user_rsa_secret_id": "test-rsa",
            "userPaillierSecretId": "test-paillier",
            "id": "da8fd868-0fed-42e3-b6d8-5abbf0864d4a",
            "proposal_id": 4,
            "stations": [
                "1"
            ],
            "files": [
                "test_train/entrypoint.py",
                "test_train/requirements.txt"
            ],
            "master_image": "python/slim",
            "entrypointExecutable": "python",
            "entrypoint_path": "test_train/entrypoint.py",
            "session_id": "8203c4facff907d3bd83f8399e9a97aa4270e27acb4369f5bcdaab20643f2dc7c2ca8fe78a576c3ae7ac56b64d89a778aa86f7f90360734965dce0264ddcd705",
            "hash": "91416369e845e7ff12efe8514736d468b71bfc15cc5ded92399a1a558f4317da68cfd5884cb9e5bbbac15ce45731afe4e47ced256c7a2e493ff7fad5481b8d31",
            "hash_signed": "ace71ecae217b8da4426cee8ba8abeddab6d1d9c9d073e7c54197b82a1d453189ca2a3e278be7747b4e0fac28bba32dc1b5a4dbc4b060a2f5e659180367b56b90b6ee8f59f529206e39645acd0bd24c03c3ef291ac8ad91dbf4390541033656ec3ee48a516a94348cb60ed596be305c3754e7e4b66dc433bb47a2483ea7d772cc6a353bb43b82e4f35f7dc6ee1f502765d64785ea816b20eed6c3a1ea857a753d5048e16d395d3479b62d91c9870d9f19ee0740b6051a3089e5350227820281406d267e188ac4edb1f0f3ebd36a0aa6cb2eeeaaa71023b0e8e6381d3bc683277208a7c91de77d61e4a8ca8f71621449e564f57bb8eaef25f08da61e8b0b79f61",
            "query": {
                "query": "/Patient?",
                "data": {
                    "output_format": "json",
                    "filename": "patients.json",
                }
            },
            "user_he_key": "12345241",
            "entrypoint_command": "run"
        }
    }


@pytest.fixture
def status_message():
    return {
        "type": "trainStatus",
        "data": {
            "userId": 5,
            "id": "test-train-1"
        },
        "metadata": {

        }
    }


def test_build_message_from_json(build_message, build_message_query):
    build_hash = build_message["data"]["hash"]
    message = BuildMessage(**build_message["data"])
    assert isinstance(message, BuildMessage)
    assert message
    assert message.hash == build_hash

    message = BuildMessage.parse_raw(json.dumps(build_message["data"]))
    assert message
    assert message.hash == build_hash

    message = BuildMessage.parse_raw(json.dumps(build_message["data"]).encode("utf-8"))
    assert message
    assert message.hash == build_hash

    with pytest.raises(ValueError):
        message = BuildMessage.parse_raw(1)

    query_message = BuildMessage(**build_message_query["data"])
    assert query_message

    query_message2 = BuildMessage.parse_raw(json.dumps(build_message_query["data"]).encode("utf-8"))

    assert query_message == query_message2
