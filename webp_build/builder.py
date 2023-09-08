import json
import platform
import tempfile
from importlib.resources import read_text
from os import path, getcwd, getenv
import platform

from cffi import FFI
from conans.client import conan_api

import webp_build

def install_libwebp(arch=None):
    # Use Conan to install libwebp

    conan, _, _ = conan_api.ConanAPIV1.factory()

    settings = []
    if platform.system() == 'Windows':
        settings.append('os=Windows')
    elif platform.system() == 'Darwin':
        settings.append('os=Macos')
        settings.append('compiler=apple-clang')
        settings.append('compiler.version=11.0')
        settings.append('compiler.libcxx=libc++')
    elif platform.system() == 'Linux':
        settings.append('os=Linux')

    if arch:
        settings.append(f'arch={arch}')

    if getenv('CIBW_BUILD') and 'musllinux' in getenv('CIBW_BUILD'):
        build_policy = ['always']
    else:
        build_policy = ['missing']

    with tempfile.TemporaryDirectory() as tmp_dir:
        conan.install(path=getcwd(), cwd=tmp_dir, settings=settings, build=build_policy)
        with open(path.join(tmp_dir, 'conanbuildinfo.json'), 'r') as f:
            conan_info = json.load(f)
    
    return conan_info

def fetch_cffi_settings(conan_info, cffi_settings):
    # Find header files and libraries in libwebp

    for dep in conan_info['dependencies']:
        for lib_name in dep['libs']:
            if platform.system() == 'Windows':
                lib_filename = '{}.lib'.format(lib_name)
            else:
                lib_filename = 'lib{}.a'.format(lib_name)
            for lib_path in dep['lib_paths']:
                candidate = path.join(lib_path, lib_filename)
                if path.isfile(candidate):
                    cffi_settings['extra_objects'].append(candidate)
                else:
                    cffi_settings['libraries'].append(lib_name)
        for include_path in dep['include_paths']:
            cffi_settings['include_dirs'].append(include_path)
    
    if  platform.system() == 'Darwin':
        cffi_settings['extra_compile_args'].append('-mmacosx-version-min=11.0')
    
    return cffi_settings

arch = None
if platform.architecture()[0] == '32bit' and platform.machine().lower() in {'amd64', 'x86_64', 'x64', 'i686'}:
    arch = 'x86'
elif getenv('CIBW_ARCHS_MACOS') and ('arm64' in getenv('CIBW_ARCHS_MACOS') or 'universal2' in getenv('CIBW_ARCHS_MACOS')):
    arch = 'armv8'
elif getenv('CIBW_ARCHS_WINDOWS') and 'ARM64' in getenv('CIBW_ARCHS_WINDOWS'):
    arch = 'armv8'

cffi_settings = {
    'extra_objects': [],
    'extra_compile_args': [],
    'include_dirs': [],
    'libraries': []
}

conan_info = install_libwebp(arch)
cffi_settings = fetch_cffi_settings(conan_info, cffi_settings)
if 'universal2' in getenv('CIBW_ARCHS_MACOS'):
    # Repeat to install the other architecture version of libwebp
    conan_info = install_libwebp('x86_64')
    cffi_settings = fetch_cffi_settings(conan_info, cffi_settings)

# Specify C sources to be built by CFFI
ffibuilder = FFI()
ffibuilder.set_source(
    '_webp',
    read_text(webp_build, 'source.c'),
    extra_objects=cffi_settings['extra_objects'],
    extra_compile_args=cffi_settings['extra_compile_args'],
    include_dirs=cffi_settings['include_dirs'],
    libraries=cffi_settings['libraries'],
)
ffibuilder.cdef(read_text(webp_build, 'cdef.h'))

if __name__ == '__main__':
    ffibuilder.compile(verbose=True)
