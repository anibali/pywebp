import json
import platform
import tempfile
from importlib.resources import read_text
from os import path, getcwd, getenv

from cffi import FFI
from conans.client import conan_api

import webp_build

conan, _, _ = conan_api.ConanAPIV1.factory()

# Use Conan to install libwebp
settings = []
build_pkgs = ['missing']
print(f'platform.architecture: {platform.architecture()}')
print(f'platform.machine: {platform.machine()}')
if platform.architecture()[0] == '32bit' and platform.machine().lower() in {'amd64', 'x86_64', 'x64', 'i686'}:
    settings.append('arch=x86')
if getenv('CIBW_ARCHS_MACOS') == 'arm64':
    # https://blog.conan.io/2021/09/21/m1.html
    settings.append('os=Macos')
    settings.append('arch=armv8')
    settings.append('compiler=apple-clang')
    settings.append('compiler.version=11.0')
    settings.append('compiler.libcxx=libc++')
elif getenv('CIBW_ARCHS_WINDOWS') == 'ARM64':
    settings.append('os=Windows')
    settings.append('arch=armv8')
elif getenv('CIBW_ARCHS_LINUX') not in (None, 'x86_64', 'aarch64') or getenv('CIBW_ARCHS_WINDOWS') not in (None, 'AMD64'):
    # Windows: Only x86_64 works
    # Linux: CMake binaries are only provided for x86_64 and armv8 architectures
    build_pkgs.append('cmake')

with tempfile.TemporaryDirectory() as tmp_dir:
    conan.install(path=getcwd(), cwd=tmp_dir, settings=settings, build=build_pkgs,
                  profile_names=[path.abspath('conan_profile')])
    with open(path.join(tmp_dir, 'conanbuildinfo.json'), 'r') as f:
        conan_info = json.load(f)

print(conan_info)

# Find header files and libraries in libwebp
extra_objects = []
extra_compile_args = []
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

if getenv('CIBW_ARCHS_MACOS') == 'arm64':
    extra_compile_args.append('--target=arm64-apple-macos11')

print('CFFI arguments:')
print(f'{extra_objects = }')
print(f'{extra_compile_args = }')
print(f'{include_dirs = }')
print(f'{libraries = }')

# Specify C sources to be built by CFFI
ffibuilder = FFI()
ffibuilder.set_source(
    '_webp',
    read_text(webp_build, 'source.c'),
    extra_objects=extra_objects,
    extra_compile_args=extra_compile_args,
    include_dirs=include_dirs,
    libraries=libraries,
)
ffibuilder.cdef(read_text(webp_build, 'cdef.h'))


if __name__ == '__main__':
    ffibuilder.compile(verbose=True)
