#!/bin/bash

# Change into project directory
cd "$(dirname "${BASH_SOURCE[0]}")/../"

# Remove build artifacts
rm -rf build/
rm -rf dist/
rm -rf *.egg-info/
rm -f _webp.abi3.so
