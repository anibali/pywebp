import json
import platform
from importlib.resources import read_text
import os
import subprocess
import platform
import shutil

from cffi import FFI

import webp_build

PYWEBP_COMPILE_TARGET = os.getenv('PYWEBP_COMPILE_TARGET')
conan_archs = {
    'x86_64': ['amd64', 'x86_64', 'x64'],
    'x86': ['i386', 'i686', 'x86'],
    'armv8': ['arm64', 'aarch64', 'aarch64_be', 'armv8b', 'armv8l'],
    'ppc64le': ['ppc64le', 'powerpc'],
    's390x': ['s390', 's390x']
}

def get_arch():
    arch = None
    if PYWEBP_COMPILE_TARGET:
        arch = PYWEBP_COMPILE_TARGET
    elif platform.architecture()[0] == '32bit' and platform.machine().lower() in conan_archs['x86'] + conan_archs['x86_64']:
        arch = 'x86'
    else:
        for k, v in conan_archs.items():
            if platform.machine().lower() in v:
                arch = k
                break
    
    return arch

def install_libwebp(arch=None):
    # Use Conan to install libwebp

    settings = []

    if platform.system() == 'Windows':
        settings.append('os=Windows')
    elif platform.system() == 'Darwin':
        settings.append('os=Macos')
        if arch == 'x86_64':
            settings.append('os.version=10.9')
        else:
            settings.append('os.version=11.0')
        settings.append('compiler=apple-clang')
        settings.append('compiler.libcxx=libc++')
    elif platform.system() == 'Linux':
        settings.append('os=Linux')

    if arch:
        settings.append(f'arch={arch}')

    build = ['missing']
    if os.path.isdir('/lib') and len([i for i in os.listdir('/lib') if i.startswith('libc.musl')]) != 0:
        # Need to compile libwebp if musllinux
        build.append('libwebp*')
        
    if (not shutil.which('cmake') and 
        (platform.architecture()[0] == '32bit' or 
        platform.machine().lower() not in (conan_archs['armv8'] + conan_archs['x86']))):

        build.append('cmake*')
    
    subprocess.run(['conan', 'profile', 'detect'])
    result = subprocess.run([
        'conan', 'install', 
        *[x for s in settings for x in ('-s', s)],
        *[x for b in build for x in ('-b', b)],
        '-of', 'conan_output', '--deployer=direct_deploy', '--format=json', '.'
        ], stdout=subprocess.PIPE).stdout.decode()
    # print(result)
    conan_info = json.loads(result)
    
    return conan_info

def fetch_cffi_settings(conan_info, cffi_settings):
    # Find header files and libraries in libwebp

    for dep in conan_info['graph']['nodes'].values():
        if dep.get('package_folder') == None:
            continue
        
        for lib, i in reversed(dep['cpp_info'].items()):
            for include_dir in dep['cpp_info'][lib].get('includedirs', []):
                cffi_settings['include_dirs'].append(include_dir) if include_dir not in cffi_settings['include_dirs'] else None

            if not i.get('libs'):
                continue

            for lib_name in i.get('libs'):
                if platform.system() == 'Windows':
                    lib_filename = '{}.lib'.format(lib_name)
                else:
                    lib_filename = 'lib{}.a'.format(lib_name)
                
                if not i.get('libdirs'):
                    continue

                for lib_dir in i.get('libdirs'):
                    lib_path = os.path.join(lib_dir, lib_filename)
                    if os.path.isfile(lib_path):
                        cffi_settings['extra_objects'].append(lib_path)
                    else:
                        cffi_settings['libraries'].append(lib_name)
    
    print(f'{cffi_settings = }')
    
    return cffi_settings

cffi_settings = {
    'extra_objects': [],
    'extra_compile_args': [],
    'include_dirs': [],
    'libraries': []
}

arch = get_arch()
if platform.system() == 'Darwin':
    if arch == 'x86_64':
        cffi_settings['extra_compile_args'].append('-mmacosx-version-min=10.9')
    else:
        cffi_settings['extra_compile_args'].append('-mmacosx-version-min=11.0')


if PYWEBP_COMPILE_TARGET == 'universal2':
    conan_info = install_libwebp('x86_64')
    cffi_settings = fetch_cffi_settings(conan_info, cffi_settings)
    conan_info = install_libwebp('armv8')
    cffi_settings = fetch_cffi_settings(conan_info, cffi_settings)
else:
    conan_info = install_libwebp(arch)
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
