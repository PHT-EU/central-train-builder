#!/usr/bin/env python
import os
import typing

_FILE_PREFIX = 'SUMMAND'
_RESULT_FILE = 'SUM'
_RESOURCE_VOLUME_PHT_TEST_VOLUME = 'PHT_RESOURCE_PHT_TEST_VOLUME'


def get_input_dir():
    return os.environ[_RESOURCE_VOLUME_PHT_TEST_VOLUME]

def list_dir() -> typing.Iterable[str]:
    d = get_input_dir()
    for f in os.listdir(d):
        if f.startswith(_FILE_PREFIX):
            yield os.path.join(d, f)

def number_from_file(filename):
    with open(filename) as f:
        return int(f.read())

def compute_sum():
    return sum(number_from_file(f) for f in list_dir())

if __name__ == '__main__':
    s = compute_sum()
    with open(_RESULT_FILE, 'a') as f:
        f.write(f'{s}\n')

