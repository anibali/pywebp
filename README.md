# WebP Python bindings

[![CircleCI](https://img.shields.io/circleci/project/github/anibali/pywebp.svg)](https://circleci.com/gh/anibali/pywebp)
[![license](https://img.shields.io/github/license/anibali/pywebp.svg)](https://github.com/anibali/pywebp/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/webp)](https://pypi.org/project/webp/)
[![GitHub](https://img.shields.io/github/stars/anibali/pywebp?style=social)](https://github.com/anibali/pywebp)

## Installation

```sh
pip install webp
```

### Requirements

* [libwebp](https://github.com/webmproject/libwebp) (tested with v1.0.3)
  - Install libwebpmux and libwebpdemux components as well.
  - Check out the Dockerfile for steps to build from source on Ubuntu.
* Python 3 (tested with v3.6)
* cffi
* Pillow
* numpy

## Usage

```python
import webp
```

### Simple API

```python
# Save an image
webp.save_image(img, 'image.webp', quality=80)

# Load an image
img = webp.load_image('image.webp', 'RGBA')

# Save an animation
webp.save_images(imgs, 'anim.webp', fps=10, lossless=True)

# Load an animation
imgs = webp.load_images('anim.webp', 'RGB', fps=10)
```

If you prefer working with numpy arrays, use the functions `imwrite`, `imread`, `mimwrite`,
and `mimread` instead.

### Advanced API

```python
# Encode a PIL image to WebP in memory, with encoder hints
pic = webp.WebPPicture.from_pil(img)
config = WebPConfig.new(preset=webp.WebPPreset.PHOTO, quality=70)
buf = pic.encode(config).buffer()

# Read a WebP file and decode to a BGR numpy array
with open('image.webp', 'rb') as f:
  webp_data = webp.WebPData.from_buffer(f.read())
  arr = webp_data.decode(color_mode=WebPColorMode.BGR)

# Save an animation
enc = webp.WebPAnimEncoder.new(width, height)
timestamp_ms = 0
for img in imgs:
  pic = webp.WebPPicture.from_pil(img)
  enc.encode_frame(pic, timestamp_ms)
  timestamp_ms += 250
anim_data = enc.assemble(timestamp_ms)
with open('anim.webp', 'wb') as f:
  f.write(anim_data.buffer())

# Load an animation
with open('anim.webp', 'rb') as f:
  webp_data = webp.WebPData.from_buffer(f.read())
  dec = webp.WebPAnimDecoder.new(webp_data)
  for arr, timestamp_ms in dec.frames():
    # `arr` contains decoded pixels for the frame
    # `timestamp_ms` contains the _end_ time of the frame
    pass
```

## Features

* Picture encoding/decoding
* Animation encoding/decoding
* Automatic memory management
* Simple API for working with `PIL.Image` objects

### Not implemented

* Encoding/decoding still images in YUV color mode
* Advanced muxing/demuxing (color profiles, etc.)
* Expose all useful fields

## Developer notes

### Running tests

The CircleCI local CLI should be used to run tests in an isolated environment:

```console
$ circleci local execute
```

### Cutting releases

Source release:

```console
$ python setup.py sdist
$ twine upload dist/webp-*.tar.gz
```

Linux binary wheel release (repeat for different Python versions and architectures):

```console
$ docker run -i -t -v `pwd`:/io quay.io/pypa/manylinux2014_x86_64 /bin/bash
# cd io
# /opt/python/cp36-cp36m/bin/python setup.py bdist_wheel
# /opt/python/cp36-cp36m/bin/pip install dist/webp-*-cp36-cp36m-linux_x86_64.whl
# /opt/python/cp36-cp36m/bin/pip install pytest
# /opt/python/cp36-cp36m/bin/pytest tests
# auditwheel repair dist/webp-*-cp36-cp36m-linux_x86_64.whl -w dist
# exit
$ twine upload dist/webp-*-cp36-cp36m-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

## Known issues

* An animation where all frames are identical will "collapse" in on itself,
  resulting in a single frame. Unfortunately, WebP seems to discard timestamp
  information in this case, which breaks `webp.load_images` when the FPS
  is specified.
