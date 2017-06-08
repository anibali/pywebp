#!/bin/bash

# Change into project directory
cd "$(dirname "${BASH_SOURCE[0]}")/../"

# Package and upload to PyPI
docker-compose run --rm python ./setup.py sdist upload
