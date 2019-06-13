#!/bin/bash

set -e
set -u
set -o pipefail

PYTHONPATH=. coverage run --source . \
             -m pytest \
             -s tests/mx.mxtests/mx_mxtests.py