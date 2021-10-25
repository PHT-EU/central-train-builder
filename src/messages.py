import json
from abc import ABC, abstractmethod
from typing import Union, List


class Message(ABC):
    message_id: str
    type: str
    metadata: dict
    data: dict

    @classmethod
    @abstractmethod
    def from_json(cls, json_message: Union[dict, str, bytes]):
        pass

    @abstractmethod
    def to_json(self):
        pass


class BuildMessage(Message):
    train_id: str
    proposal_id: int
    stations: List[str]
    files: List[str]
    master_image: str
    entrypoint_executable: str
    entrypoint_path: str
    session_id: str
    hash: str
    hash_signed: str
    query: dict
    user_he_key: str

    @classmethod
    def from_json(cls, json_message: Union[dict, str, bytes]):
        message_dict = load_json_dict(json_message)
        cls.message_id = message_dict.get("id")
        cls.type = message_dict.get("type")
        cls.data = message_dict.get("data")
        cls.metadata = message_dict.get("metadata")
        cls.train_id = cls.data["trainId"]
        cls.proposal_id = cls.data["proposalId"]
        cls.stations = cls.data["stations"]
        cls.files = cls.data["files"]
        cls.master_image = cls.data["masterImage"]
        cls.entrypoint_executable = cls.data["entrypointExecutable"]
        cls.entrypoint_path = cls.data["entrypointPath"]
        cls.session_id = cls.data["sessionId"]
        cls.hash = cls.data["hash"]
        cls.hash_signed = cls.data["hashSigned"]
        return cls

    def to_json(self):
        return json.dumps(
            {
                "id": self.message_id,
                "type": self.type,
                "metadata": self.metadata,
                "data": self.data
            }
        )


def load_json_dict(json_message: Union[dict, str, bytes]) -> dict:
    if isinstance(json_message, dict):
        return json_message
    elif isinstance(json_message, str) or isinstance(json_message, bytes):
        return json.loads(json_message)
    else:
        raise ValueError(f"Can not load dictionary from message with type {type(json_message)}")
