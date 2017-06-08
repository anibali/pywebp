#!/usr/bin/env python3

from setuptools import setup, find_packages
import unittest

def all_tests():
  test_loader = unittest.TestLoader()
  test_suite = test_loader.discover('tests', pattern='test_*.py')
  return test_suite

setup(
  name='webp',
  version='0.1.0a1',
  packages=find_packages(),
  author='Aiden Nibali',
  description='Python bindings for WebP',
  test_suite='setup.all_tests',
  setup_requires=['cffi>=1.0.0'],
  cffi_modules=['webp/webp_build.py:ffibuilder'],
  install_requires=['cffi>=1.0.0', 'Pillow>=4.0.0', 'numpy>=1.0.0'],
)
