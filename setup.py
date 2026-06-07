"""Setuptools entry point for building the WebP extension."""

import sys
from pathlib import Path

from setuptools import setup

sys.path.append(str(Path(__file__).parent))


if __name__ == "__main__":
    setup(
        zip_safe=False,
        cffi_modules=["webp_build/builder.py:ffibuilder"],
        options={"bdist_wheel": {"py_limited_api": "cp38"}},
    )
