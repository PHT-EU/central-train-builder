import json
from pydantic import BaseModel, StrBytes, Protocol
from typing import Union, List, Type, Optional, Callable, Any


class BuildMessage(BaseModel):
    message_id: Optional[str] = None
    type: str
    metadata: dict
    data: dict
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
    query: Optional[dict] = None
    user_he_key: Optional[str] = None

    @classmethod
    def parse_raw(cls: Type['BuildMessage'], b: StrBytes, *, content_type: str = None, encoding: str = 'utf8',
                  proto: Protocol = None, allow_pickle: bool = False) -> 'BuildMessage':

        if content_type == "str" and encoding != "utf8":
            return cls.from_json(b.encode(encoding))

        return cls.from_json(b)

    @classmethod
    def from_json(cls: Type['BuildMessage'], json_message: Union[dict, str, bytes]) -> 'BuildMessage':
        message_dict = load_json_dict(json_message)
        data = message_dict.get("data")
        return cls(
            message_id=message_dict.get("id"),
            type=message_dict.get("type"),
            data=message_dict.get("data"),
            metadata=message_dict.get("metadata"),
            train_id=data["trainId"],
            proposal_id=data["proposalId"],
            stations=data["stations"],
            files=data["files"],
            master_image=data["masterImage"],
            entrypoint_executable=data["entrypointExecutable"],
            entrypoint_path=data["entrypointPath"],
            session_id=data["sessionId"],
            hash=data["hash"],
            hash_signed=data["hashSigned"],
            query=data.get("query"),
            user_he_key=data.get("user_he_key")
        )


def load_json_dict(json_message: Union[dict, str, bytes]) -> dict:
    if isinstance(json_message, dict):
        return json_message
    elif isinstance(json_message, str) or isinstance(json_message, bytes):
        return json.loads(json_message)
    else:
        raise ValueError(f"Can not load dictionary from message with type {type(json_message)}")
