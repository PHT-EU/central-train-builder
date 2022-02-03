import json
from pydantic import BaseModel, StrBytes, Protocol
from typing import Union, List, Type, Optional, Callable, Any
from enum import Enum


class BuilderCommands(str, Enum):
    START = "trainBuildStart"
    STOP = "trainBuildStop"
    STATUS = "trainBuildStatus"


class BuildStatus(str, Enum):
    STARTED = "trainBuildStarted"
    FAILED = "trainBuildFailed"
    FINISHED = "trainBuildFinished"
    NOT_FOUND = "trainNotFound"
    STOPPED = "trainBuildStopped"


class MessageData(BaseModel):
    message: str
    id: str


class QueueMessage(BaseModel):
    type: BuilderCommands
    data: Optional[dict] = None
    metadata: Optional[dict] = None


class BuilderResponse(BaseModel):
    type: BuildStatus
    data: Optional[dict] = None
    metadata: Optional[dict] = None


class RouterMessage(BaseModel):
    type: str
    data: Optional[dict] = None
    metadata: Optional[dict] = None


class BuildMessage(BaseModel):
    id: str
    user_id: Union[str, int]
    user_rsa_secret_id: str
    user_paillier_secret_id: Optional[str] = None
    proposal_id: Union[int, str]
    stations: List[str]
    files: List[str]
    master_image: str
    entrypoint_command: str
    entrypoint_path: str
    entrypoint_command_arguments: Optional[List[str]] = None
    session_id: str
    hash: str
    hash_signed: str
    query: Optional[dict] = None

    # @classmethod
    # def parse_raw(cls: Type['BuildMessage'], b: StrBytes, *, content_type: str = None, encoding: str = 'utf8',
    #               proto: Protocol = None, allow_pickle: bool = False) -> 'BuildMessage':
    #     if content_type == "str" and encoding != "utf8":
    #         return cls.from_json(b.encode(encoding))
    #
    #     return cls.from_json(b)
    #
    # @classmethod
    # def from_json(cls: Type['BuildMessage'], json_message: Union[dict, str, bytes]) -> 'BuildMessage':
    #     message_dict = load_json_dict(json_message)
    #     data = message_dict.get("data")
    #     return cls(
    #         type=message_dict.get("type"),
    #         data=data,
    #         metadata=message_dict.get("metadata"),
    #         id=data["id"],
    #         user_id=data["userId"],
    #         user_paillier_secret_id=data.get("userPaillierSecretId"),
    #         user_rsa_secret_id=data.get("userRsaSecretId"),
    #         proposal_id=data["proposalId"],
    #         stations=data["stations"],
    #         files=data["files"],
    #         master_image=data["masterImage"],
    #         entrypoint_executable=data["entrypointExecutable"],
    #         entrypoint_args=data.get("entrypointCommandArguments"),
    #         entrypoint_path=data["entrypointPath"],
    #         session_id=data["sessionId"],
    #         hash=data["hash"],
    #         hash_signed=data["hashSigned"],
    #         query=data.get("query"),
    #     )


def load_json_dict(json_message: Union[dict, str, bytes]) -> dict:
    if isinstance(json_message, dict):
        return json_message
    elif isinstance(json_message, str) or isinstance(json_message, bytes):
        return json.loads(json_message)
    else:
        raise ValueError(f"Can not load dictionary from message with type {type(json_message)}")
