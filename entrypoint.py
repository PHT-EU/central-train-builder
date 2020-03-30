#!/usr/bin/env python
import os

_WORKDIR = '.'
_PREFIX = 'SUMMAND'
_RESULT_FILE = 'SUM'

def number_from_file(filename):
    with open(filename) as f:
        return int(f.read())

def compute_sum():
    return sum(number_from_file(f) for f in os.listdir(_WORKDIR) if f.startswith(_PREFIX))

if __name__ == '__main__':
    s = compute_sum()
    with open(_RESULT_FILE, 'a') as f:
        f.write(f'{s}\n')