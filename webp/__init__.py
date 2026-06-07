"""Python bindings for the WebP image format."""

from enum import Enum
from os import PathLike
from pathlib import Path
from typing import Any, Generator, List, Optional, Tuple, Union

import numpy as np
from PIL import Image

from webp._webp import ffi, lib

GRAYSCALE_DIMENSIONS = 2
COLOR_DIMENSIONS = 3
PACKED_COLOR_BYTES = 2
RGB_CHANNELS = 3
RGBA_CHANNELS = 4

FilePath = Union[str, PathLike]
_Pointer = Any


class WebPPreset(Enum):
    """Represent WebP encoder presets."""

    DEFAULT = lib.WEBP_PRESET_DEFAULT  # Default
    PICTURE = lib.WEBP_PRESET_PICTURE  # Indoor photo, portrait-like
    PHOTO = lib.WEBP_PRESET_PHOTO  # Outdoor photo with natural lighting
    DRAWING = lib.WEBP_PRESET_DRAWING  # Drawing with high-contrast details
    ICON = lib.WEBP_PRESET_ICON  # Small-sized colourful image
    TEXT = lib.WEBP_PRESET_TEXT  # Text-like


class WebPColorMode(Enum):
    """Represent WebP decoder color modes."""

    RGB = lib.MODE_RGB
    RGBA = lib.MODE_RGBA
    BGR = lib.MODE_BGR
    BGRA = lib.MODE_BGRA
    ARGB = lib.MODE_ARGB
    RGBA_4444 = lib.MODE_RGBA_4444
    RGB_565 = lib.MODE_RGB_565
    rgbA = lib.MODE_rgbA  # noqa: N815
    bgrA = lib.MODE_bgrA  # noqa: N815
    Argb = lib.MODE_Argb
    rgbA_4444 = lib.MODE_rgbA_4444  # noqa: N815
    YUV = lib.MODE_YUV
    YUVA = lib.MODE_YUVA
    LAST = lib.MODE_LAST


class WebPError(Exception):
    """Represent an error raised by the WebP bindings."""


class WebPConfig:
    """Represent WebP encoder configuration."""

    DEFAULT_QUALITY: float = 75.0

    def __init__(self, ptr: _Pointer) -> None:
        """Initialize the wrapper."""
        self.ptr = ptr

    @property
    def lossless(self) -> bool:
        """Return whether lossless encoding is enabled."""
        return self.ptr.lossless != 0

    @lossless.setter
    def lossless(self, lossless: bool) -> None:
        """Return whether lossless encoding is enabled."""
        self.ptr.lossless = 1 if lossless else 0

    @property
    def quality(self) -> float:
        """Return the encoder quality."""
        return self.ptr.quality

    @quality.setter
    def quality(self, quality: float) -> None:
        """Return the encoder quality."""
        self.ptr.quality = quality

    @property
    def method(self) -> int:
        """Return the encoder method."""
        return self.ptr.method

    @method.setter
    def method(self, method: int) -> None:
        """Return the encoder method."""
        self.ptr.method = method

    @property
    def target_size(self) -> int:
        """Return the target encoded size."""
        return self.ptr.target_size

    @target_size.setter
    def target_size(self, target_size: int) -> None:
        """Return the target encoded size."""
        self.ptr.target_size = target_size

    @property
    def passes(self) -> int:
        """Return the number of analysis passes."""
        return getattr(self.ptr, "pass")

    @passes.setter
    def passes(self, passes: int) -> None:
        """Return the number of analysis passes."""
        setattr(self.ptr, "pass", passes)

    def validate(self) -> bool:
        """Return whether the configuration is valid."""
        return lib.WebPValidateConfig(self.ptr) != 0

    @staticmethod
    def new(  # noqa: PLR0913
        preset: WebPPreset = WebPPreset.DEFAULT,
        quality: Optional[float] = None,
        *,
        lossless: bool = False,
        lossless_preset: Optional[int] = None,
        method: Optional[int] = None,
        target_size: Optional[int] = None,
        passes: Optional[int] = None,
    ) -> "WebPConfig":
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
        ptr = ffi.new("WebPConfig*")
        if lib.WebPConfigPreset(ptr, preset.value, WebPConfig.DEFAULT_QUALITY) == 0:
            msg = "failed to load config options from preset"
            raise WebPError(msg)

        if lossless_preset is not None:
            if not lossless:
                msg = "can only use lossless preset when lossless is True"
                raise WebPError(msg)
            if lib.WebPConfigLosslessPreset(ptr, lossless_preset) == 0:
                msg = "failed to load config options from lossless preset"
                raise WebPError(msg)

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
            msg = "config is not valid"
            raise WebPError(msg)
        return config


class WebPData:
    """Represent encoded WebP data."""

    def __init__(self, ptr: _Pointer, data_ref: _Pointer) -> None:
        """Initialize the wrapper."""
        self.ptr = ptr
        self._data_ref = data_ref

    @property
    def size(self) -> int:
        """Return the data size in bytes."""
        return self.ptr.size

    def buffer(self) -> bytes:
        """Return the data as bytes."""
        return ffi.buffer(self._data_ref, self.size)

    def decode(self, color_mode: WebPColorMode = WebPColorMode.RGBA) -> "np.ndarray[Any, np.dtype[np.uint8]]":
        """Decode the WebP data into a numpy array."""
        dec_config = WebPDecoderConfig.new()
        dec_config.read_features(self)

        if color_mode in {
            WebPColorMode.RGBA,
            WebPColorMode.bgrA,
            WebPColorMode.BGRA,
            WebPColorMode.rgbA,
            WebPColorMode.ARGB,
            WebPColorMode.Argb,
        }:
            bytes_per_pixel = RGBA_CHANNELS
        elif color_mode in {WebPColorMode.RGB, WebPColorMode.BGR}:
            bytes_per_pixel = RGB_CHANNELS
        elif color_mode in {
            WebPColorMode.RGB_565,
            WebPColorMode.RGBA_4444,
            WebPColorMode.rgbA_4444,
        }:
            bytes_per_pixel = PACKED_COLOR_BYTES
        else:
            msg = f"unsupported color mode: {color_mode!s}"
            raise WebPError(msg)

        arr = np.empty(
            (dec_config.input.height, dec_config.input.width, bytes_per_pixel),
            dtype=np.uint8,
        )
        dec_config.output.colorspace = color_mode.value
        dec_config.output.u.RGBA.rgba = ffi.cast("uint8_t*", ffi.from_buffer(arr))
        dec_config.output.u.RGBA.size = arr.size
        dec_config.output.u.RGBA.stride = dec_config.input.width * bytes_per_pixel
        dec_config.output.is_external_memory = 1

        if lib.WebPDecode(self.ptr.bytes, self.size, dec_config.ptr) != lib.VP8_STATUS_OK:
            msg = "failed to decode"
            raise WebPError(msg)
        lib.WebPFreeDecBuffer(ffi.addressof(dec_config.ptr, "output"))

        return arr

    @staticmethod
    def from_buffer(buf: bytes) -> "WebPData":
        """Create WebP data from a byte buffer."""
        ptr = ffi.new("WebPData*")
        lib.WebPDataInit(ptr)
        data_ref = ffi.from_buffer(buf)
        ptr.size = len(buf)
        ptr.bytes = ffi.cast("uint8_t*", data_ref)
        return WebPData(ptr, data_ref)


# This internal class wraps a WebPData struct in its "unfinished" state (ie
# before bytes and size have been set)
class _WebPData:
    def __init__(self) -> None:
        """Initialize the wrapper."""
        self.ptr = ffi.new("WebPData*")
        lib.WebPDataInit(self.ptr)

    # Call this after the struct has been filled in
    def done(self, free_func: _Pointer = lib.WebPFree) -> WebPData:
        """Run done."""
        if self.ptr is None:
            msg = "_WebPData.done() called after ownership was already transferred"
            raise RuntimeError(msg)
        webp_data = WebPData(self.ptr, ffi.gc(self.ptr.bytes, free_func))
        self.ptr = None
        return webp_data


class WebPMemoryWriter:
    """Wrap a WebP memory writer."""

    def __init__(self, ptr: _Pointer) -> None:
        """Initialize the wrapper."""
        self.ptr = ptr

    def __del__(self) -> None:
        # Free memory if we are still responsible for it.
        """Release owned WebP resources."""
        if self.ptr:
            lib.WebPMemoryWriterClear(self.ptr)

    def to_webp_data(self) -> WebPData:
        """Transfer writer memory into WebP data."""
        if self.ptr is None:
            msg = "WebPMemoryWriter.to_webp_data() can only be called once"
            raise RuntimeError(msg)
        _webp_data = _WebPData()
        if _webp_data.ptr is None:
            msg = "failed to initialize WebPData"
            raise RuntimeError(msg)
        _webp_data.ptr.bytes = self.ptr.mem
        _webp_data.ptr.size = self.ptr.size
        self.ptr = None
        return _webp_data.done()

    @staticmethod
    def new() -> "WebPMemoryWriter":
        """Create a new wrapper instance."""
        ptr = ffi.new("WebPMemoryWriter*")
        lib.WebPMemoryWriterInit(ptr)
        return WebPMemoryWriter(ptr)


class WebPPicture:
    """Represent a WebP picture."""

    def __init__(self, ptr: _Pointer) -> None:
        """Initialize the wrapper."""
        self.ptr = ptr

    def __del__(self) -> None:
        """Release owned WebP resources."""
        lib.WebPPictureFree(self.ptr)

    def encode(self, config: Optional[WebPConfig] = None) -> WebPData:
        """Encode the picture as WebP data."""
        if config is None:
            config = WebPConfig.new()
        writer = WebPMemoryWriter.new()
        self.ptr.writer = ffi.addressof(lib, "WebPMemoryWrite")
        self.ptr.custom_ptr = writer.ptr
        if lib.WebPEncode(config.ptr, self.ptr) == 0:
            raise WebPError("encoding error: " + self.ptr.error_code)
        return writer.to_webp_data()

    def save(self, file_path: FilePath, config: Optional[WebPConfig] = None) -> None:
        """Save the picture to a WebP file."""
        buf = self.encode(config).buffer()
        with Path(file_path).open("wb") as f:
            f.write(buf)

    @staticmethod
    def new(width: int, height: int) -> "WebPPicture":
        """Create a new wrapper instance."""
        ptr = ffi.new("WebPPicture*")
        if lib.WebPPictureInit(ptr) == 0:
            msg = "version mismatch"
            raise WebPError(msg)
        ptr.width = width
        ptr.height = height
        if lib.WebPPictureAlloc(ptr) == 0:
            msg = "memory error"
            raise WebPError(msg)
        return WebPPicture(ptr)

    @staticmethod
    def from_numpy(arr: "np.ndarray[Any, np.dtype[np.uint8]]", *, pilmode: Optional[str] = None) -> "WebPPicture":
        """Create a picture from a numpy array."""
        ptr = ffi.new("WebPPicture*")
        if lib.WebPPictureInit(ptr) == 0:
            msg = "version mismatch"
            raise WebPError(msg)

        if len(arr.shape) == COLOR_DIMENSIONS:
            bytes_per_pixel = arr.shape[-1]
        elif len(arr.shape) == GRAYSCALE_DIMENSIONS:
            bytes_per_pixel = 1
        else:
            raise WebPError("unexpected array shape: " + repr(arr.shape))

        if pilmode is None:
            if bytes_per_pixel == RGB_CHANNELS:
                import_func = lib.WebPPictureImportRGB
            elif bytes_per_pixel == RGBA_CHANNELS:
                import_func = lib.WebPPictureImportRGBA
            else:
                raise WebPError("cannot infer color mode from array of shape " + repr(arr.shape))
        elif pilmode == "RGB":
            import_func = lib.WebPPictureImportRGB
        elif pilmode == "RGBA":
            import_func = lib.WebPPictureImportRGBA
        else:
            raise WebPError("unsupported image mode: " + pilmode)

        ptr.height, ptr.width = arr.shape[:2]
        pixels = ffi.cast("uint8_t*", ffi.from_buffer(arr))
        stride = ptr.width * bytes_per_pixel
        ptr.use_argb = 1
        if import_func(ptr, pixels, stride) == 0:
            msg = "memory error"
            raise WebPError(msg)
        return WebPPicture(ptr)

    @staticmethod
    def from_pil(img: Image.Image) -> "WebPPicture":
        """Create a picture from a PIL image."""
        if img.mode == "P":
            mode = "RGBA" if "transparency" in img.info else "RGB"
            img = img.convert(mode)
        return WebPPicture.from_numpy(np.asarray(img), pilmode=img.mode)


class WebPDecoderConfig:
    """Wrap a WebP decoder configuration."""

    def __init__(self, ptr: _Pointer) -> None:
        """Initialize the wrapper."""
        self.ptr = ptr

    @property
    def input(self) -> _Pointer:
        """Return decoder input settings."""
        return self.ptr.input

    @property
    def output(self) -> _Pointer:
        """Return decoder output settings."""
        return self.ptr.output

    @property
    def options(self) -> _Pointer:
        """Return decoder options."""
        return self.ptr.options

    def read_features(self, webp_data: WebPData) -> None:
        """Read WebP features into this configuration."""
        input_ptr = ffi.addressof(self.ptr, "input")
        if lib.WebPGetFeatures(webp_data.ptr.bytes, webp_data.size, input_ptr) != lib.VP8_STATUS_OK:
            msg = "failed to read features"
            raise WebPError(msg)

    @staticmethod
    def new() -> "WebPDecoderConfig":
        """Create a new wrapper instance."""
        ptr = ffi.new("WebPDecoderConfig*")
        if lib.WebPInitDecoderConfig(ptr) == 0:
            msg = "failed to init decoder config"
            raise WebPError(msg)
        return WebPDecoderConfig(ptr)


class WebPAnimEncoderOptions:
    """Represent WebP animation encoder options."""

    def __init__(self, ptr: _Pointer) -> None:
        """Initialize the wrapper."""
        self.ptr = ptr

    @property
    def loop_count(self) -> int:
        """Return the animation loop count."""
        return self.ptr.anim_params.loop_count

    @loop_count.setter
    def loop_count(self, loop_count: int) -> None:
        """Return the animation loop count."""
        self.ptr.anim_params.loop_count = loop_count

    @property
    def minimize_size(self) -> bool:
        """Return whether size minimization is enabled."""
        return self.ptr.minimize_size != 0

    @minimize_size.setter
    def minimize_size(self, minimize_size: bool) -> None:
        """Return whether size minimization is enabled."""
        self.ptr.minimize_size = 1 if minimize_size else 0

    @property
    def allow_mixed(self) -> bool:
        """Return whether mixed compression is enabled."""
        return self.ptr.allow_mixed != 0

    @allow_mixed.setter
    def allow_mixed(self, allow_mixed: bool) -> None:
        """Return whether mixed compression is enabled."""
        self.ptr.allow_mixed = 1 if allow_mixed else 0

    @staticmethod
    def new(*, minimize_size: bool = False, allow_mixed: bool = False) -> "WebPAnimEncoderOptions":
        """Create a new wrapper instance."""
        ptr = ffi.new("WebPAnimEncoderOptions*")
        if lib.WebPAnimEncoderOptionsInit(ptr) == 0:
            msg = "version mismatch"
            raise WebPError(msg)
        enc_opts = WebPAnimEncoderOptions(ptr)
        enc_opts.minimize_size = minimize_size
        enc_opts.allow_mixed = allow_mixed
        return enc_opts


class WebPAnimEncoder:
    """Encode animated WebP images."""

    def __init__(self, ptr: _Pointer, enc_opts: WebPAnimEncoderOptions) -> None:
        """Initialize the wrapper."""
        self.ptr = ptr
        self.enc_opts = enc_opts

    def __del__(self) -> None:
        """Release owned WebP resources."""
        lib.WebPAnimEncoderDelete(self.ptr)

    def encode_frame(self, frame: WebPPicture, timestamp_ms: int, config: Optional[WebPConfig] = None) -> None:
        """Add a frame to the animation.

        Args:
            frame (WebPPicture): Frame image.
            timestamp_ms (int): When the frame should be shown (in milliseconds).
            config (WebPConfig): Encoder configuration.
        """
        if config is None:
            config = WebPConfig.new()
        if lib.WebPAnimEncoderAdd(self.ptr, frame.ptr, timestamp_ms, config.ptr) == 0:
            raise WebPError("encoding error: " + self.ptr.error_code)

    def assemble(self, end_timestamp_ms: int) -> WebPData:
        """Assemble encoded animation data."""
        if lib.WebPAnimEncoderAdd(self.ptr, ffi.NULL, end_timestamp_ms, ffi.NULL) == 0:
            raise WebPError("encoding error: " + self.ptr.error_code)
        _webp_data = _WebPData()
        if lib.WebPAnimEncoderAssemble(self.ptr, _webp_data.ptr) == 0:
            msg = "error assembling animation"
            raise WebPError(msg)
        return _webp_data.done()

    @staticmethod
    def new(width: int, height: int, enc_opts: Optional[WebPAnimEncoderOptions] = None) -> "WebPAnimEncoder":
        """Create a new wrapper instance."""
        if enc_opts is None:
            enc_opts = WebPAnimEncoderOptions.new()
        ptr = lib.WebPAnimEncoderNew(width, height, enc_opts.ptr)
        return WebPAnimEncoder(ptr, enc_opts)


class WebPAnimDecoderOptions:
    """Represent WebP animation decoder options."""

    def __init__(self, ptr: _Pointer) -> None:
        """Initialize the wrapper."""
        self.ptr = ptr

    @property
    def color_mode(self) -> WebPColorMode:
        """Return the decoder color mode."""
        return WebPColorMode(self.ptr.color_mode)

    @color_mode.setter
    def color_mode(self, color_mode: WebPColorMode) -> None:
        """Return the decoder color mode."""
        self.ptr.color_mode = color_mode.value

    @property
    def use_threads(self) -> bool:
        """Return whether threaded decoding is enabled."""
        return self.ptr.use_threads != 0

    @use_threads.setter
    def use_threads(self, use_threads: bool) -> None:
        """Return whether threaded decoding is enabled."""
        self.ptr.use_threads = 1 if use_threads else 0

    @staticmethod
    def new(*, use_threads: bool = False, color_mode: WebPColorMode = WebPColorMode.RGBA) -> "WebPAnimDecoderOptions":
        """Create a new wrapper instance."""
        ptr = ffi.new("WebPAnimDecoderOptions*")
        if lib.WebPAnimDecoderOptionsInit(ptr) == 0:
            msg = "version mismatch"
            raise WebPError(msg)
        dec_opts = WebPAnimDecoderOptions(ptr)
        dec_opts.use_threads = use_threads
        dec_opts.color_mode = color_mode
        return dec_opts


class WebPAnimInfo:
    """Represent WebP animation metadata."""

    def __init__(self, ptr: _Pointer) -> None:
        """Initialize the wrapper."""
        self.ptr = ptr

    @property
    def frame_count(self) -> int:
        """Return the number of animation frames."""
        return self.ptr.frame_count

    @property
    def width(self) -> int:
        """Return the canvas width."""
        return self.ptr.canvas_width

    @property
    def height(self) -> int:
        """Return the canvas height."""
        return self.ptr.canvas_height

    @property
    def loop_count(self) -> int:
        """Return the animation loop count."""
        return self.ptr.loop_count

    @staticmethod
    def new() -> "WebPAnimInfo":
        """Create a new wrapper instance."""
        ptr = ffi.new("WebPAnimInfo*")
        return WebPAnimInfo(ptr)


class WebPAnimDecoder:
    """Decode animated WebP images."""

    def __init__(self, ptr: _Pointer, dec_opts: WebPAnimDecoderOptions, anim_info: WebPAnimInfo) -> None:
        """Initialize the wrapper."""
        self.ptr = ptr
        self.dec_opts = dec_opts
        self.anim_info = anim_info

    def __del__(self) -> None:
        """Release owned WebP resources."""
        lib.WebPAnimDecoderDelete(self.ptr)

    def has_more_frames(self) -> bool:
        """Return whether more frames are available."""
        return lib.WebPAnimDecoderHasMoreFrames(self.ptr) != 0

    def reset(self) -> None:
        """Reset the decoder to the first frame."""
        lib.WebPAnimDecoderReset(self.ptr)

    def decode_frame(self) -> Tuple["np.ndarray[Any, np.dtype[np.uint8]]", int]:
        """Decodes the next frame of the animation.

        Returns:
            numpy.array: The frame image.
            float: The timestamp for the end of the frame.
        """
        timestamp_ptr = ffi.new("int*")
        buf_ptr = ffi.new("uint8_t**")
        if lib.WebPAnimDecoderGetNext(self.ptr, buf_ptr, timestamp_ptr) == 0:
            msg = "decoding error"
            raise WebPError(msg)
        size = self.anim_info.height * self.anim_info.width * 4
        buf = ffi.buffer(buf_ptr[0], size)
        arr = np.copy(np.frombuffer(buf, dtype=np.uint8))
        arr = np.reshape(arr, (self.anim_info.height, self.anim_info.width, 4))
        # timestamp_ms contains the _end_ time of this frame
        timestamp_ms = timestamp_ptr[0]
        return arr, timestamp_ms

    def frames(
        self,
    ) -> Generator[Tuple["np.ndarray[Any, np.dtype[np.uint8]]", int], None, None]:
        """Yield decoded animation frames."""
        while self.has_more_frames():
            arr, timestamp_ms = self.decode_frame()
            yield arr, timestamp_ms

    @staticmethod
    def new(webp_data: WebPData, dec_opts: Optional[WebPAnimDecoderOptions] = None) -> "WebPAnimDecoder":
        """Create a new wrapper instance."""
        if dec_opts is None:
            dec_opts = WebPAnimDecoderOptions.new()
        ptr = lib.WebPAnimDecoderNew(webp_data.ptr, dec_opts.ptr)
        if ptr == ffi.NULL:
            msg = "failed to create decoder"
            raise WebPError(msg)
        anim_info = WebPAnimInfo.new()
        if lib.WebPAnimDecoderGetInfo(ptr, anim_info.ptr) == 0:
            msg = "failed to get animation info"
            raise WebPError(msg)
        return WebPAnimDecoder(ptr, dec_opts, anim_info)


def imwrite(
    file_path: FilePath,
    arr: "np.ndarray[Any, np.dtype[np.uint8]]",
    pilmode: Optional[str] = None,
    **kwargs: Any,  # noqa: ANN401
) -> None:
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


def imread(file_path: FilePath, pilmode: str = "RGBA") -> "np.ndarray[Any, np.dtype[np.uint8]]":
    """Load from file and decode numpy array with WebP.

    Args:
        file_path (str): File to load from.
        pilmode (str): Image color mode (RGBA, RGBa, or RGB).

    Returns:
        np.ndarray: The decoded image data.
    """
    if pilmode == "RGBA":
        color_mode = WebPColorMode.RGBA
    elif pilmode == "RGBa":
        color_mode = WebPColorMode.rgbA
    elif pilmode == "RGB":
        color_mode = WebPColorMode.RGB
    else:
        raise WebPError("unsupported color mode: " + pilmode)

    with Path(file_path).open("rb") as f:
        webp_data = WebPData.from_buffer(f.read())
        return webp_data.decode(color_mode=color_mode)


def _mimwrite_pics(
    file_path: FilePath,
    pics: List[WebPPicture],
    fps: float = 30.0,
    loop_count: Optional[int] = None,
    **kwargs: Any,  # noqa: ANN401
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

    with Path(file_path).open("wb") as f:
        f.write(anim_data.buffer())


def mimwrite(
    file_path: FilePath,
    arrs: "List[np.ndarray[Any, np.dtype[np.uint8]]]",
    fps: float = 30.0,
    loop_count: Optional[int] = None,
    pilmode: Optional[str] = None,
    **kwargs: Any,  # noqa: ANN401
) -> None:
    """Encode a sequence of PIL Images with WebP and save to file.

    Args:
        file_path (str): File to save to.
        arrs (list of np.ndarray): Image data to save.
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
    file_path: FilePath,
    fps: Optional[float] = None,
    *,
    use_threads: bool = True,
    pilmode: str = "RGBA",
) -> List["np.ndarray[Any, np.dtype[np.uint8]]"]:
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
    if pilmode == "RGBA":
        color_mode = WebPColorMode.RGBA
    elif pilmode == "RGBa":
        color_mode = WebPColorMode.rgbA
    elif pilmode == "RGB":
        # NOTE: RGB decoding of animations is currently not supported by
        # libwebpdemux. Hence we will read RGBA and remove the alpha channel later.
        color_mode = WebPColorMode.RGBA
    else:
        raise WebPError("unsupported color mode: " + pilmode)

    arrs: List[np.ndarray[Any, np.dtype[np.uint8]]] = []

    with Path(file_path).open("rb") as f:
        webp_data = WebPData.from_buffer(f.read())
        dec_opts = WebPAnimDecoderOptions.new(use_threads=use_threads, color_mode=color_mode)
        dec = WebPAnimDecoder.new(webp_data, dec_opts)
        eps = 1e-7

        for arr, frame_end_time in dec.frames():
            frame = arr[:, :, 0:3] if pilmode == "RGB" else arr
            if fps is None:
                arrs.append(frame)
            else:
                while len(arrs) * (1000 / fps) + eps < frame_end_time:
                    arrs.append(frame)

    return arrs


def save_image(
    img: Image.Image,
    file_path: FilePath,
    **kwargs: Any,  # noqa: ANN401
) -> None:
    """Encode PIL Image with WebP and save to file.

    Args:
        img (pil.Image): Image to save.
        file_path (str): File to save to.
        kwargs: Keyword arguments for encoder settings (see `WebPConfig.new`).
    """
    pic = WebPPicture.from_pil(img)
    config = WebPConfig.new(**kwargs)
    pic.save(file_path, config)


def load_image(file_path: FilePath, mode: str = "RGBA") -> Image.Image:
    """Load from file and decode PIL Image with WebP.

    Args:
        file_path (str): File to load from.
        mode (str): Mode for the PIL image (RGBA, RGBa, or RGB).

    Returns:
        PIL.Image: The decoded Image.
    """
    arr = imread(file_path, pilmode=mode)
    return Image.fromarray(arr, mode)


def save_images(
    imgs: List[Image.Image],
    file_path: FilePath,
    **kwargs: Any,  # noqa: ANN401
) -> None:
    """Encode a sequence of PIL Images with WebP and save to file.

    Args:
        imgs (list of pil.Image): Images to save.
        file_path (str): File to save to.
        kwargs: Keyword arguments for saving the images (see `mimwrite`).
    """
    pics = [WebPPicture.from_pil(img) for img in imgs]
    _mimwrite_pics(file_path, pics, **kwargs)


def load_images(
    file_path: FilePath,
    mode: str = "RGBA",
    **kwargs: Any,  # noqa: ANN401
) -> List[Image.Image]:
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
