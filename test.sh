#!/bin/bash
source .venv/bin/activate
source tests/.env
python3 tests/test_route.py "$@"
