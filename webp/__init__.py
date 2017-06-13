import numpy as np
from enum import Enum
from PIL import Image

from _webp import ffi, lib

class WebPPreset(Enum):
  DEFAULT = lib.WEBP_PRESET_DEFAULT # Default
  PICTURE = lib.WEBP_PRESET_PICTURE # Indoor photo, portrait-like
  PHOTO   = lib.WEBP_PRESET_PHOTO   # Outdoor photo with natural lighting
  DRAWING = lib.WEBP_PRESET_DRAWING # Drawing with high-contrast details
  ICON    = lib.WEBP_PRESET_ICON    # Small-sized colourful image
  TEXT    = lib.WEBP_PRESET_TEXT    # Text-like

class WebPColorMode(Enum):
  RGB       = lib.MODE_RGB
  RGBA      = lib.MODE_RGBA
  BGR       = lib.MODE_BGR
  BGRA      = lib.MODE_BGRA
  ARGB      = lib.MODE_ARGB
  RGBA_4444 = lib.MODE_RGBA_4444
  RGB_565   = lib.MODE_RGB_565
  rgbA      = lib.MODE_rgbA
  bgrA      = lib.MODE_bgrA
  Argb      = lib.MODE_Argb
  rgbA_4444 = lib.MODE_rgbA_4444
  YUV       = lib.MODE_YUV
  YUVA      = lib.MODE_YUVA
  LAST      = lib.MODE_LAST

class WebPError(Exception):
  pass

class WebPConfig:
  def __init__(self, ptr):
    self.ptr = ptr

  @property
  def lossless(self):
    return self.ptr.lossless != 0

  @lossless.setter
  def lossless(self, lossless):
    self.ptr.lossless = 1 if lossless else 0

  @property
  def quality(self):
    return self.ptr.quality

  @quality.setter
  def quality(self, quality):
    self.ptr.quality = quality

  def validate(self):
    return lib.WebPValidateConfig(self.ptr) != 0

  @staticmethod
  def new(preset=WebPPreset.DEFAULT, quality=75, lossless=False):
    ptr = ffi.new('WebPConfig*')
    if lib.WebPConfigPreset(ptr, preset.value, quality) == 0:
      raise WebPError('failed to load config from preset')
    config = WebPConfig(ptr)
    config.lossless = lossless
    if not config.validate():
      raise WebPError('config is not valid')
    return config

class WebPData:
  def __init__(self, ptr, data_ref):
    self.ptr = ptr
    self._data_ref = data_ref

  @property
  def size(self):
    return self.ptr.size

  def buffer(self):
    buf = ffi.buffer(self._data_ref, self.size)
    return buf

  def decode(self, color_mode=WebPColorMode.RGBA):
    dec_config = WebPDecoderConfig.new()
    dec_config.read_features(self)

    if color_mode == WebPColorMode.RGBA \
    or color_mode == WebPColorMode.bgrA \
    or color_mode == WebPColorMode.BGRA \
    or color_mode == WebPColorMode.rgbA \
    or color_mode == WebPColorMode.ARGB \
    or color_mode == WebPColorMode.Argb:
      bytes_per_pixel = 4
    elif color_mode == WebPColorMode.RGB \
    or color_mode == WebPColorMode.BGR:
      bytes_per_pixel = 3
    elif color_mode == WebPColorMode.RGB_565 \
    or color_mode == WebPColorMode.RGBA_4444 \
    or color_mode == WebPColorMode.rgbA_4444:
      bytes_per_pixel = 2
    else:
      raise WebPError('unsupported color mode: ' + color_mode)

    arr = np.empty((dec_config.input.height, dec_config.input.width, bytes_per_pixel), dtype=np.uint8)
    dec_config.output.colorspace = color_mode.value
    dec_config.output.u.RGBA.rgba = ffi.cast('uint8_t*', ffi.from_buffer(arr))
    dec_config.output.u.RGBA.size = arr.size
    dec_config.output.u.RGBA.stride = dec_config.input.width * bytes_per_pixel
    dec_config.output.is_external_memory = 1

    if lib.WebPDecode(self.ptr.bytes, self.size, dec_config.ptr) != lib.VP8_STATUS_OK:
      raise WebPError('failed to decode')
    lib.WebPFreeDecBuffer(ffi.addressof(dec_config.ptr, 'output'))

    return arr

  @staticmethod
  def from_buffer(buf):
    ptr = ffi.new('WebPData*')
    lib.WebPDataInit(ptr)
    data_ref = ffi.from_buffer(buf)
    ptr.size = len(buf)
    ptr.bytes = ffi.cast('uint8_t*', data_ref)
    return WebPData(ptr, data_ref)

# This internal class wraps a WebPData struct in its "unfinished" state (ie
# before bytes and size have been set)
class _WebPData:
  def __init__(self):
    self.ptr = ffi.new('WebPData*')
    lib.WebPDataInit(self.ptr)

  # Call this after the struct has been filled in
  def done(self, free_func=lib.WebPFree):
    webp_data = WebPData(self.ptr, ffi.gc(self.ptr.bytes, free_func))
    self.ptr = None
    return webp_data

class WebPMemoryWriter:
  def __init__(self, ptr):
    self.ptr = ptr

  def __del__(self):
    # Free memory if we are still responsible for it.
    if self.ptr:
      lib.WebPMemoryWriterClear(self.ptr)

  def to_webp_data(self):
    _webp_data = _WebPData()
    _webp_data.ptr.bytes = self.ptr.mem
    _webp_data.ptr.size = self.ptr.size
    self.ptr = None
    return _webp_data.done()

  @staticmethod
  def new():
    ptr = ffi.new('WebPMemoryWriter*')
    lib.WebPMemoryWriterInit(ptr)
    return WebPMemoryWriter(ptr)

class WebPPicture:
  def __init__(self, ptr):
    self.ptr = ptr

  def __del__(self):
    lib.WebPPictureFree(self.ptr)

  def encode(self, config=None):
    if config is None:
      config = WebPConfig.new()
    writer = WebPMemoryWriter.new()
    self.ptr.writer = ffi.addressof(lib, 'WebPMemoryWrite')
    self.ptr.custom_ptr = writer.ptr
    if lib.WebPEncode(config.ptr, self.ptr) == 0:
      raise WebPError('encoding error: ' + self.ptr.error_code)
    return writer.to_webp_data()

  @staticmethod
  def new(width, height):
    ptr = ffi.new('WebPPicture*')
    if lib.WebPPictureInit(ptr) == 0:
      raise WebPError('version mismatch')
    ptr.width = width
    ptr.height = height
    if lib.WebPPictureAlloc(ptr) == 0:
      raise WebPError('memory error')
    return WebPPicture(ptr)

  @staticmethod
  def from_pil(img):
    ptr = ffi.new('WebPPicture*')
    if lib.WebPPictureInit(ptr) == 0:
      raise WebPError('version mismatch')
    ptr.width = img.width
    ptr.height = img.height

    if img.mode == 'RGB':
      import_func = lib.WebPPictureImportRGB
      bytes_per_pixel = 3
    elif img.mode == 'RGBA':
      import_func = lib.WebPPictureImportRGBA
      bytes_per_pixel = 4
    else:
      raise WebPError('unsupported image mode: ' + img.mode)

    arr = np.asarray(img, dtype=np.uint8)
    pixels = ffi.cast('uint8_t*', ffi.from_buffer(arr))
    stride = img.width * bytes_per_pixel
    ptr.use_argb = 1
    if import_func(ptr, pixels, stride) == 0:
      raise WebPError('memory error')
    return WebPPicture(ptr)

class WebPDecoderConfig:
  def __init__(self, ptr):
    self.ptr = ptr

  @property
  def input(self):
    return self.ptr.input

  @property
  def output(self):
    return self.ptr.output

  @property
  def options(self):
    return self.ptr.options

  def read_features(self, webp_data):
    input_ptr = ffi.addressof(self.ptr, 'input')
    if lib.WebPGetFeatures(webp_data.ptr.bytes, webp_data.size, input_ptr) != lib.VP8_STATUS_OK:
      raise WebPError('failed to read features')

  @staticmethod
  def new():
    ptr = ffi.new('WebPDecoderConfig*')
    if lib.WebPInitDecoderConfig(ptr) == 0:
      raise WebPError('failed to init decoder config')
    return WebPDecoderConfig(ptr)

class WebPAnimEncoderOptions:
  def __init__(self, ptr):
    self.ptr = ptr

  @property
  def minimize_size(self):
    return self.ptr.minimize_size != 0

  @minimize_size.setter
  def minimize_size(self, minimize_size):
    self.ptr.minimize_size = 1 if minimize_size else 0

  @property
  def allow_mixed(self):
    return self.ptr.allow_mixed != 0

  @allow_mixed.setter
  def allow_mixed(self, allow_mixed):
    self.ptr.allow_mixed = 1 if allow_mixed else 0

  @staticmethod
  def new(minimize_size=False, allow_mixed=False):
    ptr = ffi.new('WebPAnimEncoderOptions*')
    if lib.WebPAnimEncoderOptionsInit(ptr) == 0:
      raise WebPError('version mismatch')
    enc_opts = WebPAnimEncoderOptions(ptr)
    enc_opts.minimize_size = minimize_size
    enc_opts.allow_mixed = allow_mixed
    return enc_opts

class WebPAnimEncoder:
  def __init__(self, ptr, enc_opts):
    self.ptr = ptr
    self.enc_opts = enc_opts

  def __del__(self):
    lib.WebPAnimEncoderDelete(self.ptr)

  def encode_frame(self, frame, timestamp_ms, config=None):
    """Add a frame to the animation.

    Args:
      frame (WebPPicture): Frame image.
      timestamp_ms (int): When the frame should be shown (in milliseconds).
      config (WebPConfig): Encoder configuration.
    """
    if config is None:
      config = WebPConfig.new()
    if lib.WebPAnimEncoderAdd(self.ptr, frame.ptr, timestamp_ms, config.ptr) == 0:
      raise WebPError('encoding error: ' + self.ptr.error_code)

  def assemble(self, end_timestamp_ms):
    if lib.WebPAnimEncoderAdd(self.ptr, ffi.NULL, end_timestamp_ms, ffi.NULL) == 0:
      raise WebPError('encoding error: ' + self.ptr.error_code)
    _webp_data = _WebPData()
    if lib.WebPAnimEncoderAssemble(self.ptr, _webp_data.ptr) == 0:
      raise WebPError('error assembling animation')
    return _webp_data.done()

  @staticmethod
  def new(width, height, enc_opts):
    ptr = lib.WebPAnimEncoderNew(width, height, enc_opts.ptr)
    return WebPAnimEncoder(ptr, enc_opts)

class WebPAnimDecoderOptions:
  def __init__(self, ptr):
    self.ptr = ptr

  @property
  def color_mode(self):
    return WebPColorMode(self.ptr.color_mode)

  @color_mode.setter
  def color_mode(self, color_mode):
    self.ptr.color_mode = color_mode.value

  @property
  def use_threads(self):
    return self.ptr.use_threads != 0

  @use_threads.setter
  def use_threads(self, use_threads):
    self.ptr.use_threads = 1 if use_threads else 0

  @staticmethod
  def new(use_threads=False, color_mode=WebPColorMode.RGBA):
    ptr = ffi.new('WebPAnimDecoderOptions*')
    if lib.WebPAnimDecoderOptionsInit(ptr) == 0:
      raise WebPError('version mismatch')
    dec_opts = WebPAnimDecoderOptions(ptr)
    dec_opts.use_threads = use_threads
    dec_opts.color_mode = color_mode
    return dec_opts

class WebPAnimInfo:
  def __init__(self, ptr):
    self.ptr = ptr

  @property
  def frame_count(self):
    return self.ptr.frame_count

  @property
  def width(self):
    return self.ptr.canvas_width

  @property
  def height(self):
    return self.ptr.canvas_height

  @staticmethod
  def new():
    ptr = ffi.new('WebPAnimInfo*')
    return WebPAnimInfo(ptr)

class WebPAnimDecoder:
  def __init__(self, ptr, dec_opts, anim_info):
    self.ptr = ptr
    self.dec_opts = dec_opts
    self.anim_info = anim_info

  def __del__(self):
    lib.WebPAnimDecoderDelete(self.ptr)

  def has_more_frames(self):
    return lib.WebPAnimDecoderHasMoreFrames(self.ptr) != 0

  def reset(self):
    lib.WebPAnimDecoderReset(self.ptr)

  def decode_frame(self):
    """Decodes the next frame of the animation.

    Returns:
      numpy.array: The frame image.
      float: The timestamp for the end of the frame.
    """
    timestamp_ptr = ffi.new('int*')
    buf_ptr = ffi.new('uint8_t**')
    if lib.WebPAnimDecoderGetNext(self.ptr, buf_ptr, timestamp_ptr) == 0:
      raise WebPError('decoding error')
    size = self.anim_info.height * self.anim_info.width * 4
    buf = ffi.buffer(buf_ptr[0], size)
    arr = np.copy(np.frombuffer(buf, dtype=np.uint8))
    arr = np.reshape(arr, (self.anim_info.height, self.anim_info.width, 4))
    # timestamp_ms contains the _end_ time of this frame
    timestamp_ms = timestamp_ptr[0]
    return arr, timestamp_ms

  def frames(self):
    while self.has_more_frames():
      arr, timestamp_ms = self.decode_frame()
      yield arr, timestamp_ms

  @staticmethod
  def new(webp_data, dec_opts=None):
    if dec_opts is None:
      dec_opts = WebPAnimDecoderOptions.new()
    ptr = lib.WebPAnimDecoderNew(webp_data.ptr, dec_opts.ptr)
    if ptr == ffi.NULL:
      raise WebPError('failed to create decoder')
    anim_info = WebPAnimInfo.new()
    if lib.WebPAnimDecoderGetInfo(ptr, anim_info.ptr) == 0:
      raise WebPError('failed to get animation info')
    return WebPAnimDecoder(ptr, dec_opts, anim_info)

def save_image(img, file_path, quality=75, lossless=False):
  """Encode PIL Image with WebP and save to file.

  Args:
    img (pil.Image): Image to save.
    file_path (str): File to save to.
    quality (float): Quality (0-100, where 0 is lowest quality).
    lossless (bool): Set to True for lossless compression.
  """

  pic = WebPPicture.from_pil(img)
  config = WebPConfig.new(quality=quality, lossless=lossless)
  buf = pic.encode(config).buffer()

  with open(file_path, 'wb') as f:
    f.write(buf)

def load_image(file_path, mode='RGBA'):
  """Load from file and decode PIL Image with WebP.

  Args:
    file_path (str): File to load from.
    mode (str): Mode for the PIL image (RGBA, RGBa, or RGB).

  Returns:
    PIL.Image: The decoded Image.
  """

  if mode == 'RGBA':
    color_mode = WebPColorMode.RGBA
  elif mode == 'RGBa':
    color_mode = WebPColorMode.rgbA
  elif mode == 'RGB':
    color_mode = WebPColorMode.RGB
  else:
    raise WebPError('unsupported color mode: ' + mode)

  with open(file_path, 'rb') as f:
    webp_data = WebPData.from_buffer(f.read())
    arr = webp_data.decode(color_mode=color_mode)
    img = Image.fromarray(arr, mode)
  return img

def save_images(imgs, file_path, fps=30, quality=75, lossless=False):
  """Encode a sequence of PIL Images with WebP and save to file.

  Args:
    imgs (list of pil.Image): Images to save.
    file_path (str): File to save to.
    fps (float): Animation speed in frames per second.
    quality (float): Quality (0-100, where 0 is lowest quality).
    lossless (bool): Set to True for lossless compression.
  """

  pics = [WebPPicture.from_pil(img) for img in imgs]

  enc_opts = WebPAnimEncoderOptions.new()
  enc = WebPAnimEncoder.new(imgs[0].width, imgs[0].height, enc_opts)
  config = WebPConfig.new(quality=quality, lossless=lossless)
  for i, pic in enumerate(pics):
    t = round((i * 1000) / fps)
    enc.encode_frame(pic, t, config)
  end_t = round((len(pics) * 1000) / fps)
  anim_data = enc.assemble(end_t)

  with open(file_path, 'wb') as f:
    f.write(anim_data.buffer())

def load_images(file_path, mode='RGBA', fps=None, use_threads=True):
  """Load from file and decode a sequence of PIL Images with WebP.

  Args:
    file_path (str): File to load from.
    mode (str): Mode for the PIL image (RGBA, RGBa, or RGB).
    fps (int, optional): Frames will be evenly sampled to meet this particular
      FPS. If `fps` is None, an ordered sequence of unique frames in the
      animation will be returned.
    use_threads (str): Set to False to disable multi-threaded decoding.

  Returns:
    list of PIL.Image: The decoded Images.
  """

  if mode == 'RGBA':
    color_mode = WebPColorMode.RGBA
  elif mode == 'RGBa':
    color_mode = WebPColorMode.rgbA
  elif mode == 'RGB':
    # NOTE: RGB decoding of animations is currently not supported by
    # libwebpdemux. Hence we will read RGBA and remove the alpha channel later.
    color_mode = WebPColorMode.RGBA
  else:
    raise WebPError('unsupported color mode: ' + mode)

  imgs = []

  with open(file_path, 'rb') as f:
    webp_data = WebPData.from_buffer(f.read())
    dec_opts = WebPAnimDecoderOptions.new(
      use_threads=use_threads, color_mode=color_mode)
    dec = WebPAnimDecoder.new(webp_data, dec_opts)
    eps = 1e-7
    if fps is not None:
      ft = 1000 / fps # Duration of one frame in ms

    for arr, frame_end_time in dec.frames():
      if mode == 'RGB':
        arr = arr[:, :, 0:3]
      if fps is None:
        imgs.append(Image.fromarray(arr, mode))
      else:
        while len(imgs) * ft + eps < frame_end_time:
          imgs.append(Image.fromarray(arr, mode))

  return imgs
