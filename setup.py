#!/usr/bin/env python3

from setuptools import setup, find_packages
import unittest

def all_tests():
  test_loader = unittest.TestLoader()
  test_suite = test_loader.discover('tests', pattern='test_*.py')
  return test_suite

try:
  import pypandoc
  long_description = pypandoc.convert('README.md', 'rst')
except:
  long_description = open('README.md').read()

setup(
  name='webp',
  version='0.1.0a2',
  packages=find_packages(),
  package_data={'': ['README.md', 'LICENSE']},
  author='Aiden Nibali',
  description='Python bindings for WebP',
  long_description=long_description,
  test_suite='setup.all_tests',
  setup_requires=['cffi>=1.0.0'],
  cffi_modules=['webp/webp_build.py:ffibuilder'],
  install_requires=['cffi>=1.0.0', 'Pillow>=4.0.0', 'numpy>=1.0.0'],
)
