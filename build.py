def build(setup_kwargs):
    setup_kwargs['cffi_modules'] = [
        'webp_build/builder.py:ffibuilder',
    ]
