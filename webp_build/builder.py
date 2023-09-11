import json
import os
import platform
import shutil
import subprocess
from importlib.resources import read_text

from cffi import FFI

import webp_build

# Mapping from Conan architectures to Python machine types
CONAN_ARCHS = {
    'x86_64': ['amd64', 'x86_64', 'x64'],
    'x86': ['i386', 'i686', 'x86'],
    'armv8': ['arm64', 'aarch64', 'aarch64_be', 'armv8b', 'armv8l'],
    'ppc64le': ['ppc64le', 'powerpc'],
    's390x': ['s390', 's390x'],
}


def get_arch() -> str:
    """Get the Conan compilation target architecture.

    If not explicitly set using the `PYWEBP_COMPILE_TARGET` environment variable, this will be determined using the
    host machine's platform information.
    """
    env_arch = os.getenv('PYWEBP_COMPILE_TARGET', '')
    if env_arch:
        return env_arch

    if (
        platform.architecture()[0] == '32bit'
        and platform.machine().lower() in (CONAN_ARCHS['x86'] + CONAN_ARCHS['x86_64'])
    ):
        return 'x86'

    for k, v in CONAN_ARCHS.items():
        if platform.machine().lower() in v:
            return k

    raise RuntimeError('Unable to determine the compilation target architecture')


def install_libwebp(arch: str) -> dict:
    """Install libwebp using Conan.
    """
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

    settings.append(f'arch={arch}')

    build = ['missing']
    if os.path.isdir('/lib') and len([i for i in os.listdir('/lib') if i.startswith('libc.musl')]) != 0:
        # Need to compile libwebp if musllinux
        build.append('libwebp*')
        
    if (
        not shutil.which('cmake') and (
            platform.architecture()[0] == '32bit' or
            platform.machine().lower() not in (CONAN_ARCHS['armv8'] + CONAN_ARCHS['x86'])
        )
    ):
        build.append('cmake*')
    
    subprocess.run(['conan', 'profile', 'detect'])

    conan_output = os.path.join('conan_output', arch)

    result = subprocess.run([
        'conan', 'install', 
        *[x for s in settings for x in ('-s', s)],
        *[x for b in build for x in ('-b', b)],
        '-of', conan_output, '--deployer=direct_deploy', '--format=json', '.'
        ], stdout=subprocess.PIPE).stdout.decode()
    conan_info = json.loads(result)
    
    return conan_info


def fetch_cffi_settings(conan_info: dict, cffi_settings: dict):
    """Find header files and libraries in libwebp.
    """
    for dep in conan_info['graph']['nodes'].values():
        if dep.get('package_folder') is None:
            continue

        for cpp_info in reversed(dep['cpp_info'].values()):
            for include_dir in (cpp_info.get('includedirs') or []):
                if include_dir not in cffi_settings['include_dirs']:
                    cffi_settings['include_dirs'].append(include_dir)

            for lib_name in (cpp_info.get('libs') or []):
                if platform.system() == 'Windows':
                    lib_filename = '{}.lib'.format(lib_name)
                else:
                    lib_filename = 'lib{}.a'.format(lib_name)

                for lib_dir in (cpp_info.get('libdirs') or []):
                    lib_path = os.path.join(lib_dir, lib_filename)
                    if os.path.isfile(lib_path):
                        cffi_settings['extra_objects'].append(lib_path)
                    else:
                        cffi_settings['libraries'].append(lib_name)

    return cffi_settings


def create_ffibuilder():
    cffi_settings = {
        'extra_objects': [],
        'extra_compile_args': [],
        'include_dirs': [],
        'libraries': []
    }

    arch = get_arch()
    webp_build.logger.info(f'Detected system architecture as {arch}')
    if platform.system() == 'Darwin':
        if arch == 'x86_64':
            cffi_settings['extra_compile_args'].append('-mmacosx-version-min=10.9')
        else:
            cffi_settings['extra_compile_args'].append('-mmacosx-version-min=11.0')

    if arch == 'universal2':
        conan_info = install_libwebp('x86_64')
        cffi_settings = fetch_cffi_settings(conan_info, cffi_settings)
        conan_info = install_libwebp('armv8')
        cffi_settings = fetch_cffi_settings(conan_info, cffi_settings)
    else:
        conan_info = install_libwebp(arch)
        cffi_settings = fetch_cffi_settings(conan_info, cffi_settings)

    webp_build.logger.info(f'{cffi_settings=}')

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

    return ffibuilder


ffibuilder = create_ffibuilder()

if __name__ == '__main__':
    ffibuilder.compile(verbose=True)
