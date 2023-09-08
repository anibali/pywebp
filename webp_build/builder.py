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

    if os.path.isdir('/lib') and len([i for i in os.listdir('/lib') if i.startswith('libc.musl')]) != 0:
        # Need to compile libwebp if musllinux
        build_mode = '*'
    else:
        build_mode = 'missing'
    
    subprocess.run(['conan', 'profile', 'detect'])
    result = subprocess.run([
        'conan', 'install', *[x for s in settings for x in ('-s', s)], 
        '-of', 'conan_output', '--deployer=full_deploy',
        '--build', build_mode, '--format=json', '.'
        ], stdout=subprocess.PIPE).stdout.decode()
    # print(result)
    conan_info = json.loads(result)
    
    return conan_info

def fetch_cffi_settings(conan_info, cffi_settings):
    # Find header files and libraries in libwebp

    for dep in conan_info['graph']['nodes'].values():
        if dep.get('package_folder') == None:
            continue

        for lib_name, i in dep['cpp_info'].items():
            if lib_name == 'root':
                continue
            
            for include_dir in i.get('includedirs', []):
                cffi_settings['include_dirs'].append(include_dir) if include_dir not in cffi_settings['include_dirs'] else None

            lib_names = ['webpdecoder', 'webpdemux', 'webpmux', 'webp'] # DEBUG
            # for lib_name in i.get('libs', []):
            for lib_name in lib_names:
                if platform.system() == 'Windows':
                    lib_filename = '{}.lib'.format(lib_name)
                else:
                    lib_filename = 'lib{}.a'.format(lib_name)
                
                for lib_dir in i.get('libdirs', []):
                    lib_path = os.path.join(lib_dir, lib_filename)
                    if os.path.isfile(lib_path):
                        cffi_settings['extra_objects'].append(lib_path)
                    # else:
                    #     cffi_settings['libraries'].append(lib_name)
    
    if platform.system() == 'Darwin':
        cffi_settings['extra_compile_args'].append('-mmacosx-version-min=11.0')
    
    print(f'{cffi_settings = }')
    
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
