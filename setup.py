#!/usr/bin/env python3

from setuptools import setup


setup(
    cffi_modules=['webp_build/builder.py:ffibuilder'],
)
