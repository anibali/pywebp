#!/usr/bin/bash -e
#
# This script generates manylinux wheels of pywebp for multiple different Python versions. It is
# meant to be run inside a `quay.io/pypa/manylinux2014_x86_64` Docker container, like so:
#
#     $ docker run -it -v `pwd`:/io -w /io quay.io/pypa/manylinux2014_x86_64 ./build_manylinux_wheels.sh

for PYVER in cp36-cp36m cp37-cp37m cp38-cp38 cp39-cp39
do
  /opt/python/$PYVER/bin/python setup.py bdist_wheel
  /opt/python/$PYVER/bin/pip install dist/webp-*-$PYVER-linux_x86_64.whl
  /opt/python/$PYVER/bin/pip install pytest==5.4.3
  /opt/python/$PYVER/bin/pytest tests
  auditwheel repair dist/webp-*-$PYVER-linux_x86_64.whl -w dist
done
