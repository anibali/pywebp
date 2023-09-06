import json
import platform
import tempfile
from importlib.resources import read_text
from os import path, getcwd, environ

from cffi import FFI
from conans.client import conan_api

import webp_build

conan, _, _ = conan_api.ConanAPIV1.factory()

# Use Conan to install libwebp
with tempfile.TemporaryDirectory() as tmp_dir:
    settings = []
    print(f'platform.architecture: {platform.architecture()}')
    print(f'platform.machine: {platform.machine()}')
    if platform.architecture()[0] == '32bit' and platform.machine().lower() in {'amd64', 'x86_64', 'x64'}:
        settings.append('arch=x86')
    if 'arm64' in os.getenv('CIBW_ARCHS_MACOS'):
        settings.append('arch=armv8')
    conan.install(path=getcwd(), cwd=tmp_dir, settings=settings, build=['missing'],
                  profile_names=[path.abspath('conan_profile')])
    with open(path.join(tmp_dir, 'conanbuildinfo.json'), 'r') as f:
        conan_info = json.load(f)

# Find header files and libraries in libwebp
extra_objects = []
include_dirs = []
libraries = []
for dep in conan_info['dependencies']:
    for lib_name in dep['libs']:
        if platform.system() == 'Windows':
            lib_filename = '{}.lib'.format(lib_name)
        else:
            lib_filename = 'lib{}.a'.format(lib_name)
        for lib_path in dep['lib_paths']:
            candidate = path.join(lib_path, lib_filename)
            if path.isfile(candidate):
                extra_objects.append(candidate)
            else:
                libraries.append(lib_name)
    for include_path in dep['include_paths']:
        include_dirs.append(include_path)

# Specify C sources to be built by CFFI
ffibuilder = FFI()
ffibuilder.set_source(
    '_webp',
    read_text(webp_build, 'source.c'),
    extra_objects=extra_objects,
    include_dirs=include_dirs,
    libraries=libraries,
)
ffibuilder.cdef(read_text(webp_build, 'cdef.h'))


if __name__ == '__main__':
    ffibuilder.compile(verbose=True)
