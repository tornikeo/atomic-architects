#!/bin/bash
set -e
docker compose build
docker compose run -it --rm app python main.py "$@"