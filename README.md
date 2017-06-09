# WebP Python bindings

[![CircleCI](https://img.shields.io/circleci/project/github/anibali/pywebp.svg)](https://circleci.com/gh/anibali/pywebp)
[![license](https://img.shields.io/github/license/anibali/pywebp.svg)](https://github.com/anibali/pywebp/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/dm/webp.svg)](https://pypi.python.org/pypi/webp)
[![GitHub](https://img.shields.io/badge/github-anibali%2Fpywebp-blue.svg)](https://github.com/anibali/pywebp)

## Usage

### Writing a PIL image to a WebP file

```python
pic = webp.WebPPicture.from_pil(img)
buf = pic.encode().buffer()

with open('image.webp', 'wb') as f:
  f.write(buf)
```

### Reading a WebP file to a numpy array

```python
with open('image.webp', 'rb') as f:
  webp_data = webp.WebPData.from_buffer(f.read())
  arr = webp_data.decode() # Defaults to RGBA
```

### Writing an animation

```python
enc = webp.WebPAnimEncoder.new(width, height)
timestamp_ms = 0
for img in imgs:
  pic = webp.WebPPicture.from_pil(img)
  enc.encode_frame(pic, timestamp_ms)
  timestamp_ms += 250
anim_data = enc.assemble(timestamp_ms)

with open('anim.webp', 'wb') as f:
  f.write(anim_data.buffer())
```

### Reading an animation

```python
with open('anim.webp', 'rb') as f:
  webp_data = webp.WebPData.from_buffer(f.read())
  dec = webp.WebPAnimDecoder.new(webp_data)
  for arr, timestamp_ms in dec.frames():
    # `arr` contains decoded pixels for the frame
    # `timestamp_ms` contains the _end_ time of the frame
    pass
```

## Requirements

* Python 3 (tested with v3.6)
* libwebp, libwebpmux, libwebpdemux (tested with v0.6.0)
* Pillow (tested with v4.1.1)
* numpy (tested with v1.12.1)

## Features

* Still image encoding/decoding
* Animation encoding/decoding
* Automatic memory management
* Support for `PIL.Image` and `numpy.array` objects

### Not implemented

* Encoding/decoding still images in YUV color mode
* Advanced muxing/demuxing (color profiles, etc.)
* Expose all useful fields
