from enum import Enum

import numpy as np
from PIL import Image
from typing import Any, Generator, List, Optional, Tuple

from webp._webp import ffi, lib

class WebPPreset(Enum):
    DEFAULT: int = lib.WEBP_PRESET_DEFAULT  # Default
    PICTURE: int = lib.WEBP_PRESET_PICTURE  # Indoor photo, portrait-like
    PHOTO: int = lib.WEBP_PRESET_PHOTO  # Outdoor photo with natural lighting
    DRAWING: int = lib.WEBP_PRESET_DRAWING  # Drawing with high-contrast details
    ICON: int = lib.WEBP_PRESET_ICON  # Small-sized colourful image
    TEXT: int = lib.WEBP_PRESET_TEXT  # Text-like


class WebPColorMode(Enum):
    RGB: int = lib.MODE_RGB
    RGBA: int = lib.MODE_RGBA
    BGR: int = lib.MODE_BGR
    BGRA: int = lib.MODE_BGRA
    ARGB: int = lib.MODE_ARGB
    RGBA_4444: int = lib.MODE_RGBA_4444
    RGB_565: int = lib.MODE_RGB_565
    rgbA: int = lib.MODE_rgbA
    bgrA: int = lib.MODE_bgrA
    Argb: int = lib.MODE_Argb
    rgbA_4444: int = lib.MODE_rgbA_4444
    YUV: int = lib.MODE_YUV
    YUVA: int = lib.MODE_YUVA
    LAST: int = lib.MODE_LAST


class WebPError(Exception):
    pass


class WebPConfig:
    DEFAULT_QUALITY: float = 75.0

    def __init__(self, ptr: Any) -> None:
        self.ptr = ptr

    @property
    def lossless(self) -> bool:
        return self.ptr.lossless != 0

    @lossless.setter
    def lossless(self, lossless: bool) -> None:
        self.ptr.lossless = 1 if lossless else 0

    @property
    def quality(self) -> float:
        return self.ptr.quality

    @quality.setter
    def quality(self, quality: float) -> None:
        self.ptr.quality = quality

    @property
    def method(self) -> int:
        return self.ptr.method

    @method.setter
    def method(self, method: int) -> None:
        self.ptr.method = method

    @property
    def target_size(self) -> int:
        return self.ptr.target_size

    @target_size.setter
    def target_size(self, target_size: int) -> None:
        self.ptr.target_size = target_size

    @property
    def passes(self) -> int:
        return getattr(self.ptr, "pass")

    @passes.setter
    def passes(self, passes: int) -> None:
        setattr(self.ptr, "pass", passes)

    def validate(self) -> bool:
        return lib.WebPValidateConfig(self.ptr) != 0

    @staticmethod
    def new(preset: WebPPreset = WebPPreset.DEFAULT,
            quality: Optional[float] = None,
            lossless: bool = False,
            lossless_preset: Optional[int] = None,
            method: Optional[int] = None,
            *,
            target_size: Optional[int] = None,
            passes: Optional[int] = None) -> "WebPConfig":
        """Create a new WebPConfig instance to describe encoder settings.

        1. The preset is loaded, setting default values for quality factor (75.0) and compression
           method (4).

        2. If `lossless` is True and `lossless_preset` is specified, then the lossless preset with
           the specified level is loaded. This will replace the default values for quality factor
           and compression method.

        3. Values for lossless, quality, and method are set using explicitly provided arguments.
           This allows the caller to explicitly specify these settings and overrides settings from
           presets.

        Args:
            preset (WebPPreset): Preset setting.
            quality (float, optional): Quality factor (0=small but low quality, 100=high quality
                but big). Overrides presets. Effective default is 75.0.
            lossless (bool): Set to True for lossless compression.
            lossless_preset (int, optional): Lossless preset level (0=fast but big, 9=small but
                slow). Can only be specified when `lossless` is true. Sets the values for quality
                factor and compression method together. Effective default is 6.
            method (int, optional): Compression method (0=fast but big, 6=small but slow).
                Overrides presets. Effective default is 4.
            target_size (int, optional): Desired target size in bytes. When setting this, you
                will likely want to set passes to a value greater than 1 also.
            passes (int, optional): Number of entropy-analysis passes (between 1 and 10 inclusive).

        Returns:
            WebPConfig: The new WebPConfig instance.
        """
        ptr = ffi.new('WebPConfig*')
        if lib.WebPConfigPreset(ptr, preset.value, WebPConfig.DEFAULT_QUALITY) == 0:
            raise WebPError('failed to load config options from preset')

        if lossless_preset is not None:
            if not lossless:
                raise WebPError('can only use lossless preset when lossless is True')
            if lib.WebPConfigLosslessPreset(ptr, lossless_preset) == 0:
                raise WebPError('failed to load config options from lossless preset')

        config = WebPConfig(ptr)
        config.lossless = lossless

        # Override presets for explicitly specified values.
        if quality is not None:
            config.quality = quality
        if method is not None:
            config.method = method
        if target_size is not None:
            config.target_size = target_size
        if passes is not None:
            config.passes = passes

        if not config.validate():
            raise WebPError('config is not valid')
        return config


class WebPData:
    def __init__(self, ptr: Any, data_ref: Any) -> None:
        self.ptr = ptr
        self._data_ref = data_ref

    @property
    def size(self) -> int:
        return self.ptr.size

    def buffer(self) -> bytes:
        buf = ffi.buffer(self._data_ref, self.size)
        return buf

    def decode(self, color_mode: WebPColorMode = WebPColorMode.RGBA) -> "np.ndarray[Any, np.dtype[np.uint8]]":
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
            raise WebPError('unsupported color mode: {}'.format(str(color_mode)))

        arr = np.empty((dec_config.input.height, dec_config.input.width, bytes_per_pixel),
                       dtype=np.uint8)
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
    def from_buffer(buf: bytes) -> "WebPData":
        ptr = ffi.new('WebPData*')
        lib.WebPDataInit(ptr)
        data_ref = ffi.from_buffer(buf)
        ptr.size = len(buf)
        ptr.bytes = ffi.cast('uint8_t*', data_ref)
        return WebPData(ptr, data_ref)


# This internal class wraps a WebPData struct in its "unfinished" state (ie
# before bytes and size have been set)
class _WebPData:
    def __init__(self) -> None:
        self.ptr = ffi.new('WebPData*')
        lib.WebPDataInit(self.ptr)

    # Call this after the struct has been filled in
    def done(self, free_func: Any = lib.WebPFree) -> WebPData:
        webp_data = WebPData(self.ptr, ffi.gc(self.ptr.bytes, free_func))
        self.ptr = None
        return webp_data


class WebPMemoryWriter:
    def __init__(self, ptr: Any) -> None:
        self.ptr = ptr

    def __del__(self) -> None:
        # Free memory if we are still responsible for it.
        if self.ptr:
            lib.WebPMemoryWriterClear(self.ptr)

    def to_webp_data(self) -> WebPData:
        _webp_data = _WebPData()
        _webp_data.ptr.bytes = self.ptr.mem
        _webp_data.ptr.size = self.ptr.size
        self.ptr = None
        return _webp_data.done()

    @staticmethod
    def new() -> "WebPMemoryWriter":
        ptr = ffi.new('WebPMemoryWriter*')
        lib.WebPMemoryWriterInit(ptr)
        return WebPMemoryWriter(ptr)


class WebPPicture:
    def __init__(self, ptr: Any) -> None:
        self.ptr = ptr

    def __del__(self) -> None:
        lib.WebPPictureFree(self.ptr)

    def encode(self, config: Optional[WebPConfig] = None) -> WebPData:
        if config is None:
            config = WebPConfig.new()
        writer = WebPMemoryWriter.new()
        self.ptr.writer = ffi.addressof(lib, 'WebPMemoryWrite')
        self.ptr.custom_ptr = writer.ptr
        if lib.WebPEncode(config.ptr, self.ptr) == 0:
            raise WebPError('encoding error: ' + self.ptr.error_code)
        return writer.to_webp_data()

    def save(self, file_path: str, config: Optional[WebPConfig] = None) -> None:
        buf = self.encode(config).buffer()
        with open(file_path, 'wb') as f:
            f.write(buf)

    @staticmethod
    def new(width: int, height: int) -> "WebPPicture":
        ptr = ffi.new('WebPPicture*')
        if lib.WebPPictureInit(ptr) == 0:
            raise WebPError('version mismatch')
        ptr.width = width
        ptr.height = height
        if lib.WebPPictureAlloc(ptr) == 0:
            raise WebPError('memory error')
        return WebPPicture(ptr)

    @staticmethod
    def from_numpy(arr: "np.ndarray[Any, np.dtype[np.uint8]]", *, pilmode: Optional[str] = None) -> "WebPPicture":
        ptr = ffi.new('WebPPicture*')
        if lib.WebPPictureInit(ptr) == 0:
            raise WebPError('version mismatch')

        if len(arr.shape) == 3:
            bytes_per_pixel = arr.shape[-1]
        elif len(arr.shape) == 2:
            bytes_per_pixel = 1
        else:
            raise WebPError('unexpected array shape: ' + repr(arr.shape))

        if pilmode is None:
            if bytes_per_pixel == 3:
                import_func = lib.WebPPictureImportRGB
            elif bytes_per_pixel == 4:
                import_func = lib.WebPPictureImportRGBA
            else:
                raise WebPError('cannot infer color mode from array of shape ' + repr(arr.shape))
        else:
            if pilmode == 'RGB':
                import_func = lib.WebPPictureImportRGB
            elif pilmode == 'RGBA':
                import_func = lib.WebPPictureImportRGBA
            else:
                raise WebPError('unsupported image mode: ' + pilmode)

        ptr.height, ptr.width = arr.shape[:2]
        pixels = ffi.cast('uint8_t*', ffi.from_buffer(arr))
        stride = ptr.width * bytes_per_pixel
        ptr.use_argb = 1
        if import_func(ptr, pixels, stride) == 0:
            raise WebPError('memory error')
        return WebPPicture(ptr)

    @staticmethod
    def from_pil(img: Image.Image) -> "WebPPicture":
        if img.mode == 'P':
            if 'transparency' in img.info:
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
        return WebPPicture.from_numpy(np.asarray(img), pilmode=img.mode)


class WebPDecoderConfig:
    def __init__(self, ptr: Any) -> None:
        self.ptr = ptr

    @property
    def input(self) -> Any:
        return self.ptr.input

    @property
    def output(self) -> Any:
        return self.ptr.output

    @property
    def options(self) -> Any:
        return self.ptr.options

    def read_features(self, webp_data: WebPData) -> None:
        input_ptr = ffi.addressof(self.ptr, 'input')
        if lib.WebPGetFeatures(webp_data.ptr.bytes, webp_data.size,
                               input_ptr) != lib.VP8_STATUS_OK:
            raise WebPError('failed to read features')

    @staticmethod
    def new() -> "WebPDecoderConfig":
        ptr = ffi.new('WebPDecoderConfig*')
        if lib.WebPInitDecoderConfig(ptr) == 0:
            raise WebPError('failed to init decoder config')
        return WebPDecoderConfig(ptr)


class WebPAnimEncoderOptions:
    def __init__(self, ptr: Any) -> None:
        self.ptr = ptr

    @property
    def loop_count(self) -> int:
        return self.ptr.anim_params.loop_count

    @loop_count.setter
    def loop_count(self, loop_count: int) -> None:
        self.ptr.anim_params.loop_count = loop_count

    @property
    def minimize_size(self) -> bool:
        return self.ptr.minimize_size != 0

    @minimize_size.setter
    def minimize_size(self, minimize_size: bool) -> None:
        self.ptr.minimize_size = 1 if minimize_size else 0

    @property
    def allow_mixed(self) -> bool:
        return self.ptr.allow_mixed != 0

    @allow_mixed.setter
    def allow_mixed(self, allow_mixed: bool) -> None:
        self.ptr.allow_mixed = 1 if allow_mixed else 0

    @staticmethod
    def new(minimize_size: bool = False, allow_mixed: bool = False) -> "WebPAnimEncoderOptions":
        ptr = ffi.new('WebPAnimEncoderOptions*')
        if lib.WebPAnimEncoderOptionsInit(ptr) == 0:
            raise WebPError('version mismatch')
        enc_opts = WebPAnimEncoderOptions(ptr)
        enc_opts.minimize_size = minimize_size
        enc_opts.allow_mixed = allow_mixed
        return enc_opts


class WebPAnimEncoder:
    def __init__(self, ptr: Any, enc_opts: WebPAnimEncoderOptions) -> None:
        self.ptr = ptr
        self.enc_opts = enc_opts

    def __del__(self) -> None:
        lib.WebPAnimEncoderDelete(self.ptr)

    def encode_frame(self,
                     frame: WebPPicture,
                     timestamp_ms: int,
                     config: Optional[WebPConfig] = None
                     ):
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

    def assemble(self, end_timestamp_ms: int) -> WebPData:
        if lib.WebPAnimEncoderAdd(self.ptr, ffi.NULL, end_timestamp_ms, ffi.NULL) == 0:
            raise WebPError('encoding error: ' + self.ptr.error_code)
        _webp_data = _WebPData()
        if lib.WebPAnimEncoderAssemble(self.ptr, _webp_data.ptr) == 0:
            raise WebPError('error assembling animation')
        return _webp_data.done()

    @staticmethod
    def new(width: int, height: int, enc_opts: Optional[WebPAnimEncoderOptions] = None) -> "WebPAnimEncoder":
        if enc_opts is None:
            enc_opts = WebPAnimEncoderOptions.new()
        ptr = lib.WebPAnimEncoderNew(width, height, enc_opts.ptr)
        return WebPAnimEncoder(ptr, enc_opts)


class WebPAnimDecoderOptions:
    def __init__(self, ptr: Any) -> None:
        self.ptr = ptr

    @property
    def color_mode(self) -> WebPColorMode:
        return WebPColorMode(self.ptr.color_mode)

    @color_mode.setter
    def color_mode(self, color_mode: WebPColorMode) -> None:
        self.ptr.color_mode = color_mode.value

    @property
    def use_threads(self) -> bool:
        return self.ptr.use_threads != 0

    @use_threads.setter
    def use_threads(self, use_threads: bool) -> None:
        self.ptr.use_threads = 1 if use_threads else 0

    @staticmethod
    def new(use_threads: bool = False, color_mode: WebPColorMode = WebPColorMode.RGBA) -> "WebPAnimDecoderOptions":
        ptr = ffi.new('WebPAnimDecoderOptions*')
        if lib.WebPAnimDecoderOptionsInit(ptr) == 0:
            raise WebPError('version mismatch')
        dec_opts = WebPAnimDecoderOptions(ptr)
        dec_opts.use_threads = use_threads
        dec_opts.color_mode = color_mode
        return dec_opts


class WebPAnimInfo:
    def __init__(self, ptr: Any) -> None:
        self.ptr = ptr

    @property
    def frame_count(self) -> int:
        return self.ptr.frame_count

    @property
    def width(self) -> int:
        return self.ptr.canvas_width

    @property
    def height(self) -> int:
        return self.ptr.canvas_height

    @property
    def loop_count(self) -> int:
        return self.ptr.loop_count

    @staticmethod
    def new() -> "WebPAnimInfo":
        ptr = ffi.new('WebPAnimInfo*')
        return WebPAnimInfo(ptr)


class WebPAnimDecoder:
    def __init__(self, ptr: Any, dec_opts: WebPAnimDecoderOptions, anim_info: WebPAnimInfo) -> None:
        self.ptr = ptr
        self.dec_opts = dec_opts
        self.anim_info = anim_info

    def __del__(self) -> None:
        lib.WebPAnimDecoderDelete(self.ptr)

    def has_more_frames(self) -> bool:
        return lib.WebPAnimDecoderHasMoreFrames(self.ptr) != 0

    def reset(self) -> None:
        lib.WebPAnimDecoderReset(self.ptr)

    def decode_frame(self) -> Tuple["np.ndarray[Any, np.dtype[np.uint8]]", int]:
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

    def frames(self) -> Generator[Tuple["np.ndarray[Any, np.dtype[np.uint8]]", int], None, None]:
        while self.has_more_frames():
            arr, timestamp_ms = self.decode_frame()
            yield arr, timestamp_ms

    @staticmethod
    def new(webp_data: WebPData, dec_opts: Optional[WebPAnimDecoderOptions] = None) -> "WebPAnimDecoder":
        if dec_opts is None:
            dec_opts = WebPAnimDecoderOptions.new()
        ptr = lib.WebPAnimDecoderNew(webp_data.ptr, dec_opts.ptr)
        if ptr == ffi.NULL:
            raise WebPError('failed to create decoder')
        anim_info = WebPAnimInfo.new()
        if lib.WebPAnimDecoderGetInfo(ptr, anim_info.ptr) == 0:
            raise WebPError('failed to get animation info')
        return WebPAnimDecoder(ptr, dec_opts, anim_info)


def imwrite(
        file_path: str,
        arr: "np.ndarray[Any, np.dtype[np.uint8]]",
        pilmode: Optional[str] = None,
        **kwargs: Any) -> None:
    """Encode numpy array image with WebP and save to file.

    Args:
        file_path (str): File to save to.
        arr (np.ndarray): Image data to save.
        pilmode (str): PIL image mode corresponding to the data in `arr`.
        kwargs: Keyword arguments for encoder settings (see `WebPConfig.new`).
    """
    pic = WebPPicture.from_numpy(arr, pilmode=pilmode)
    config = WebPConfig.new(**kwargs)
    pic.save(file_path, config)


def imread(file_path: str, pilmode: str = 'RGBA') -> "np.ndarray[Any, np.dtype[np.uint8]]":
    """Load from file and decode numpy array with WebP.

    Args:
        file_path (str): File to load from.
        pilmode (str): Image color mode (RGBA, RGBa, or RGB).

    Returns:
        np.ndarray: The decoded image data.
    """
    if pilmode == 'RGBA':
        color_mode = WebPColorMode.RGBA
    elif pilmode == 'RGBa':
        color_mode = WebPColorMode.rgbA
    elif pilmode == 'RGB':
        color_mode = WebPColorMode.RGB
    else:
        raise WebPError('unsupported color mode: ' + pilmode)

    with open(file_path, 'rb') as f:
        webp_data = WebPData.from_buffer(f.read())
        arr = webp_data.decode(color_mode=color_mode)
    return arr


def _mimwrite_pics(
        file_path: str,
        pics: List[WebPPicture],
        fps: float = 30.0,
        loop_count: Optional[int] = None,
        **kwargs: Any
        ) -> None:
    enc_opts = WebPAnimEncoderOptions.new()
    if loop_count is not None:
        enc_opts.loop_count = loop_count
    enc = WebPAnimEncoder.new(pics[0].ptr.width, pics[0].ptr.height, enc_opts)
    config = WebPConfig.new(**kwargs)
    for i, pic in enumerate(pics):
        t = round((i * 1000) / fps)
        enc.encode_frame(pic, t, config)
    end_t = round((len(pics) * 1000) / fps)
    anim_data = enc.assemble(end_t)

    with open(file_path, 'wb') as f:
        f.write(anim_data.buffer())


def mimwrite(
        file_path: str,
        arrs: "List[np.ndarray[Any, np.dtype[np.uint8]]]",
        fps: float = 30.0,
        loop_count: Optional[int] = None,
        pilmode: Optional[str] = None,
        **kwargs: Any) -> None:
    """Encode a sequence of PIL Images with WebP and save to file.

    Args:
        file_path (str): File to save to.
        imgs (list of np.ndarray): Image data to save.
        fps (float): Animation speed in frames per second.
        loop_count (int, optional): Number of times to repeat the animation.
            0 = infinite.
        pilmode (str, optional): Image color mode (RGBA or RGB). Will be
            inferred from the images if not specified.
        kwargs: Keyword arguments for encoder settings (see `WebPConfig.new`).
    """
    pics = [WebPPicture.from_numpy(arr, pilmode=pilmode) for arr in arrs]
    _mimwrite_pics(file_path, pics, fps=fps, loop_count=loop_count, **kwargs)


def mimread(
        file_path: str,
        fps: Optional[float] = None,
        use_threads: bool = True,
        pilmode: str = 'RGBA') -> List["np.ndarray[Any, np.dtype[np.uint8]]"]:
    """Load from file and decode a list of numpy arrays with WebP.

    Args:
        file_path (str): File to load from.
        pilmode (str): Image color mode (RGBA, RGBa, or RGB).
        fps (float, optional): Frames will be evenly sampled to meet this particular
            FPS. If `fps` is None, an ordered sequence of unique frames in the
            animation will be returned.
        use_threads (bool): Set to False to disable multi-threaded decoding.

    Returns:
        list of np.ndarray: The decoded image data.
    """

    if pilmode == 'RGBA':
        color_mode = WebPColorMode.RGBA
    elif pilmode == 'RGBa':
        color_mode = WebPColorMode.rgbA
    elif pilmode == 'RGB':
        # NOTE: RGB decoding of animations is currently not supported by
        # libwebpdemux. Hence we will read RGBA and remove the alpha channel later.
        color_mode = WebPColorMode.RGBA
    else:
        raise WebPError('unsupported color mode: ' + pilmode)

    arrs: List["np.ndarray[Any, np.dtype[np.uint8]]"] = []

    with open(file_path, 'rb') as f:
        webp_data = WebPData.from_buffer(f.read())
        dec_opts = WebPAnimDecoderOptions.new(
            use_threads=use_threads, color_mode=color_mode)
        dec = WebPAnimDecoder.new(webp_data, dec_opts)
        eps = 1e-7

        for arr, frame_end_time in dec.frames():
            if pilmode == 'RGB':
                arr = arr[:, :, 0:3]
            if fps is None:
                arrs.append(arr)
            else:
                while len(arrs) * (1000 / fps) + eps < frame_end_time:
                    arrs.append(arr)

    return arrs


def save_image(img: Image.Image, file_path: str, **kwargs: Any) -> None:
    """Encode PIL Image with WebP and save to file.

    Args:
        img (pil.Image): Image to save.
        file_path (str): File to save to.
        kwargs: Keyword arguments for encoder settings (see `WebPConfig.new`).
    """
    pic = WebPPicture.from_pil(img)
    config = WebPConfig.new(**kwargs)
    pic.save(file_path, config)


def load_image(file_path: str, mode: str = 'RGBA') -> Image.Image:
    """Load from file and decode PIL Image with WebP.

    Args:
        file_path (str): File to load from.
        mode (str): Mode for the PIL image (RGBA, RGBa, or RGB).

    Returns:
        PIL.Image: The decoded Image.
    """
    arr = imread(file_path, pilmode=mode)
    return Image.fromarray(arr, mode)


def save_images(imgs: List[Image.Image], file_path: str, **kwargs: Any) -> None:
    """Encode a sequence of PIL Images with WebP and save to file.

    Args:
        imgs (list of pil.Image): Images to save.
        file_path (str): File to save to.
        kwargs: Keyword arguments for saving the images (see `mimwrite`).
    """
    pics = [WebPPicture.from_pil(img) for img in imgs]
    _mimwrite_pics(file_path, pics, **kwargs)


def load_images(file_path: str, mode: str = 'RGBA', **kwargs: Any) -> List[Image.Image]:
    """Load from file and decode a sequence of PIL Images with WebP.

    Args:
        file_path (str): File to load from.
        mode (str): Mode for the PIL image (RGBA, RGBa, or RGB).
        kwargs: Keyword arguments for loading the images (see `mimread`).

    Returns:
        list of PIL.Image: The decoded Images.
    """
    arrs = mimread(file_path, pilmode=mode, **kwargs)
    return [Image.fromarray(arr, mode) for arr in arrs]
