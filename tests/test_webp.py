import unittest

import webp

from PIL import Image, ImageDraw
import numpy as np
import os
from tempfile import TemporaryDirectory

class TestWebP(unittest.TestCase):
  def test_WebPConfig(self):
    config = webp.WebPConfig.new(webp.WebPPreset.DRAWING, 50)
    del config

  def test_WebPPicture(self):
    pic = webp.WebPPicture.new(32, 32)
    del pic

    img = Image.new('RGB', (32, 16))
    pic = webp.WebPPicture.from_pil(img)
    del pic

  def test_image(self):
    img = Image.new('RGB', (32, 16))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 7, 15], fill=(255, 0, 0))

    pic = webp.WebPPicture.from_pil(img)
    buf = pic.encode().buffer()

    with TemporaryDirectory() as tmpdir:
      file_name = os.path.join(tmpdir, 'image.webp')
      with open(file_name, 'wb') as f:
        f.write(buf)

      with open(file_name, 'rb') as f:
        webp_data = webp.WebPData.from_buffer(f.read())
        arr = webp_data.decode(color_mode=webp.WebPColorMode.RGB)

        expected = np.asarray(img, dtype=np.uint8)
        np.testing.assert_allclose(arr, expected, atol=50)

  def test_anim(self):
    imgs = []
    width = 256
    height = 64
    for i in range(4):
      img = Image.new('RGBA', (width, height))
      draw = ImageDraw.Draw(img)
      x = i * (width/4)
      draw.rectangle([x, 0, x + (width/4-1), height-1], fill=(255, 0, 0))
      imgs.append(img)

    webp_pics = [webp.WebPPicture.from_pil(img) for img in imgs]

    enc_opts = webp.WebPAnimEncoderOptions.new()
    enc = webp.WebPAnimEncoder.new(width, height, enc_opts)
    t = 0
    config = webp.WebPConfig.new(lossless=True)
    for webp_pic in webp_pics:
      enc.encode_frame(webp_pic, t, config)
      t += 250
    anim_data = enc.assemble(t)

    with TemporaryDirectory() as tmpdir:
      file_name = os.path.join(tmpdir, 'anim.webp')

      with open(file_name, 'wb') as f:
        f.write(anim_data.buffer())

      with open(file_name, 'rb') as f:
        webp_data = webp.WebPData.from_buffer(f.read())
        dec_opts = webp.WebPAnimDecoderOptions.new()
        dec = webp.WebPAnimDecoder.new(webp_data, dec_opts)
        self.assertEqual(dec.anim_info.frame_count, 4)
        for i, (arr, t) in enumerate(dec.frames()):
          expected = np.asarray(imgs[i], dtype=np.uint8)
          np.testing.assert_allclose(arr, expected, atol=50)

  def test_anim_simple(self):
    imgs = []
    width = 256
    height = 64
    for i in range(4):
      img = Image.new('RGBA', (width, height))
      draw = ImageDraw.Draw(img)
      draw.rectangle([0, 0, width-1, height-1], fill=(0, 0, 255))
      x = i * (width/4)
      draw.rectangle([x, 0, x + (width/4-1), height-1], fill=(255, 0, 0))
      imgs.append(img)

    with TemporaryDirectory() as tmpdir:
      file_name = os.path.join(tmpdir, 'anim.webp')

      webp.save_images(imgs, file_name, fps=4, lossless=True)
      dec_imgs = webp.load_images(file_name, 'RGBA')

      self.assertEqual(len(dec_imgs), 4)
      for dec_img, img in zip(dec_imgs, imgs):
        actual = np.asarray(dec_img, dtype=np.uint8)
        expected = np.asarray(img, dtype=np.uint8)
        np.testing.assert_allclose(actual, expected, atol=80)

  def test_image_simple(self):
    width = 256
    height = 64
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width-1, height-1], fill=(0, 0, 255))
    draw.rectangle([0, 0, (width/4-1), height-1], fill=(255, 0, 0))

    with TemporaryDirectory() as tmpdir:
      file_name = os.path.join(tmpdir, 'image.webp')

      webp.save_image(img, file_name, lossless=True)
      dec_img = webp.load_image(file_name, 'RGB')

      actual = np.asarray(dec_img, dtype=np.uint8)
      expected = np.asarray(img, dtype=np.uint8)
      np.testing.assert_allclose(actual, expected, atol=80)
