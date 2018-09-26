#!/usr/bin/env python3

from setuptools import setup, find_packages

try:
  import pypandoc
  long_description = pypandoc.convert('README.md', 'rst')
except:
  long_description = open('README.md').read()

setup(
  name='webp',
  version='0.1.0a8',
  url='https://github.com/anibali/pywebp',
  packages=find_packages(include=['webp', 'webp.*']),
  author='Aiden Nibali',
  description='Python bindings for WebP',
  license='MIT',
  long_description=long_description,
  test_suite='tests',
  setup_requires=['cffi>=1.0.0', 'conan>=1.7.4,<1.8.0'],
  cffi_modules=['webp/webp_build.py:ffibuilder'],
  install_requires=['cffi>=1.0.0', 'Pillow>=4.0.0', 'numpy>=1.0.0'],
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Topic :: Multimedia :: Graphics :: Graphics Conversion',
    'License :: OSI Approved :: MIT License',
  ]
)
