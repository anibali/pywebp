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
  version='0.1.0a7',
  url='https://github.com/anibali/pywebp',
  packages=find_packages(),
  author='Aiden Nibali',
  description='Python bindings for WebP',
  license='MIT',
  long_description=long_description,
  test_suite='setup.all_tests',
  setup_requires=['cffi>=1.0.0'],
  cffi_modules=['webp/webp_build.py:ffibuilder'],
  install_requires=['cffi>=1.0.0', 'Pillow>=4.0.0', 'numpy>=1.0.0'],
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Topic :: Multimedia :: Graphics :: Graphics Conversion',
    'License :: OSI Approved :: MIT License',
  ]
)
