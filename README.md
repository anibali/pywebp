# WebP Python bindings

[![CircleCI](https://img.shields.io/circleci/project/github/anibali/pywebp.svg)](https://circleci.com/gh/anibali/pywebp)
[![license](https://img.shields.io/github/license/anibali/pywebp.svg)](https://github.com/anibali/pywebp/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/dm/webp.svg)](https://pypi.python.org/pypi/webp)
[![GitHub](https://img.shields.io/badge/github-anibali%2Fpywebp-blue.svg)](https://github.com/anibali/pywebp)

## Installation

```sh
pip install webp
```

### Requirements

* [libwebp](https://github.com/webmproject/libwebp) (tested with v0.6.0)
  - Install libwebpmux and libwebpdemux components as well.
  - Check out the Dockerfile for steps to build from source on Ubuntu.
* Python 3 (tested with v3.6)
* cffi (tested with 1.10.0)
* Pillow (tested with v4.1.1)
* numpy (tested with v1.12.1)

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

## Known issues

* An animation where all frames are identical will "collapse" in on itself,
  resulting in a single frame. Unfortunately, WebP seems to discard timestamp
  information in this case, which breaks `webp.load_images` when the FPS
  is specified.
