import json
import platform
from importlib.resources import read_text
import os
import subprocess
import platform

from cffi import FFI

import webp_build

def install_libwebp(arch=None):
    # Use Conan to install libwebp

    settings = []

    if platform.system() == 'Windows':
        settings.append('-s:h os=Windows')
    elif platform.system() == 'Darwin':
        settings.append('-s:h os=Macos')
        settings.append('-s:h compiler=apple-clang')
        settings.append('-s:h compiler.version=11.0')
        settings.append('-s:h compiler.libcxx=libc++')
    elif platform.system() == 'Linux':
        settings.append('-s:h os=Linux')

    if arch:
        settings.append(f'-s:h arch={arch}')

    if os.getenv('CIBW_BUILD') and 'musllinux' in os.getenv('CIBW_BUILD'):
        settings.append('--build="*"')
    else:
        settings.append('--build=missing')
    
    result = subprocess.run(['conan', 'install', *settings, '--format=json', '.'], stdout=subprocess.PIPE).stdout.decode()
    conan_info = json.loads(result)
    
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
                candidate = os.path.join(lib_path, lib_filename)
                if os.path.isfile(candidate):
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
elif os.getenv('CIBW_ARCHS_MACOS') and ('arm64' in os.getenv('CIBW_ARCHS_MACOS') or 'universal2' in os.getenv('CIBW_ARCHS_MACOS')):
    arch = 'armv8'
elif os.getenv('CIBW_ARCHS_WINDOWS') and 'ARM64' in os.getenv('CIBW_ARCHS_WINDOWS'):
    arch = 'armv8'

cffi_settings = {
    'extra_objects': [],
    'extra_compile_args': [],
    'include_dirs': [],
    'libraries': []
}

conan_info = install_libwebp(arch)
cffi_settings = fetch_cffi_settings(conan_info, cffi_settings)
if os.getenv('CIBW_ARCHS_MACOS') and 'universal2' in os.getenv('CIBW_ARCHS_MACOS'):
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
