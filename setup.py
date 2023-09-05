import os
import sys

from setuptools import setup

sys.path.append(os.path.join(os.path.dirname(__file__)))


if __name__ == '__main__':
    setup(
        zip_safe=False,
        cffi_modules=['webp_build/builder.py:ffibuilder'],
    )
