#!/bin/bash

# Change into project directory
cd "$(dirname "${BASH_SOURCE[0]}")/../"

# Clean old outputs
scripts/clean.sh

# Package and upload to PyPI
docker-compose run --rm python ./setup.py sdist upload
