# WebP Python bindings

[![Build status](https://img.shields.io/endpoint.svg?url=https%3A%2F%2Factions-badge.atrox.dev%2Fanibali%2Fpywebp%2Fbadge&label=build&logo=none)](https://actions-badge.atrox.dev/anibali/pywebp/goto)
[![License](https://img.shields.io/github/license/anibali/pywebp.svg)](https://github.com/anibali/pywebp/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/webp)](https://pypi.org/project/webp/)
[![GitHub](https://img.shields.io/github/stars/anibali/pywebp?style=social)](https://github.com/anibali/pywebp)

## Installation

```sh
pip install webp
```

On Windows you may encounter the following error during installation:

```
conans.errors.ConanException: 'settings.compiler' value not defined
```

This means that you need to install a C compiler and configure Conan so that it knows which
compiler to use. See https://github.com/anibali/pywebp/issues/20 for more details.

### Requirements

* Python 3.8+

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

### Setting up

1. Install `mamba` and `conda-lock`. The easiest way to do this is by installing
   [Mambaforge](https://github.com/conda-forge/miniforge#mambaforge) and then
   running `mamba install conda-lock`. 
2. Create and activate the Conda environment:
   ```console
   $ conda-lock install -n webp
   $ mamba activate webp
   ```
3. Install PyPI dependencies:
   ```console
   $ poetry install
   ```

### Running tests

```console
$ pytest tests/
```

### Cutting a new release

1. Ensure that tests are passing and everything is ready for release.
2. Create and push a Git tag:
   ```console
   $ git tag v0.1.6
   $ git push --tags
   ```
3. Download the artifacts from GitHub Actions, which will include the source distribution tarball and binary wheels.
4. Create a new release on GitHub from the tagged commit and upload the packages as attachments to the release.
5. Also upload the packages to PyPI using Twine:
   ```console
   $ twine upload webp-*.tar.gz webp-*.whl
   ```
6. Bump the version number in `pyproject.toml` and create a commit, signalling the start of development on the next version.

These files should also be added to a GitHub release.

## Known issues

* An animation where all frames are identical will "collapse" in on itself,
  resulting in a single frame. Unfortunately, WebP seems to discard timestamp
  information in this case, which breaks `webp.load_images` when the FPS
  is specified.
* There are currently no 32-bit binaries of libwebp uploaded to Conan Center. If you are running
  32-bit Python, libwebp will be built from source.
