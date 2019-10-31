import os
from dataclasses import dataclass


__all__ = [
    'Config'
]


@dataclass(frozen=True)
class Config:
    upload_dir: str

    @classmethod
    def from_env(cls):
        upload_dir = _get_or_raise('UPLOAD_DIR')
        _check_upload_dir(upload_dir)

        return cls(
            upload_dir=upload_dir)


def _get_or_raise(key) -> str:
    if key not in os.environ:
        raise ConfigurationException(f'Required key not in environment: {key}')
    return os.environ[key]


@dataclass(frozen=True)
class ConfigurationException(Exception):
    msg: str


def _check_upload_dir(upload_dir: str):
    if not os.path.isdir(upload_dir):
        raise ConfigurationException("Upload dir is not a directory")
