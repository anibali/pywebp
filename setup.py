#!/usr/bin/env python3

import os
import sys

from setuptools import setup

sys.path.insert(0, os.path.dirname(__file__))

setup(
    cffi_modules=['webp_build/builder.py:ffibuilder'],
)
