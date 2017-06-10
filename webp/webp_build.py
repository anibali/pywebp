from cffi import FFI
ffibuilder = FFI()

ffibuilder.set_source("_webp",
  r"""
    #include <webp/decode.h>
    #include <webp/demux.h>
    #include <webp/encode.h>
    #include <webp/mux.h>

    #if WEBP_ENCODER_ABI_VERSION <= 0x0206
    void WebPFree(void* ptr) {
      free(ptr);
    }
    #endif

    #if WEBP_ENCODER_ABI_VERSION <= 0x0203
    void WebPMemoryWriterClear(WebPMemoryWriter* writer) {
      free(writer->mem);
    }
    #endif
  """,
  libraries=['webp', 'webpdemux', 'webpmux'])

ffibuilder.cdef("""
  typedef enum WebPPreset {
    WEBP_PRESET_DEFAULT = 0,
    WEBP_PRESET_PICTURE,
    WEBP_PRESET_PHOTO,
    WEBP_PRESET_DRAWING,
    WEBP_PRESET_ICON,
    WEBP_PRESET_TEXT
  } WebPPreset;

  typedef enum WEBP_CSP_MODE {
    MODE_RGB = 0, MODE_RGBA = 1,
    MODE_BGR = 2, MODE_BGRA = 3,
    MODE_ARGB = 4, MODE_RGBA_4444 = 5,
    MODE_RGB_565 = 6,
    MODE_rgbA = 7,
    MODE_bgrA = 8,
    MODE_Argb = 9,
    MODE_rgbA_4444 = 10,
    MODE_YUV = 11, MODE_YUVA = 12,
    MODE_LAST = 13
  } WEBP_CSP_MODE;

  typedef enum VP8StatusCode {
    VP8_STATUS_OK = 0,
    VP8_STATUS_OUT_OF_MEMORY,
    VP8_STATUS_INVALID_PARAM,
    VP8_STATUS_BITSTREAM_ERROR,
    VP8_STATUS_UNSUPPORTED_FEATURE,
    VP8_STATUS_SUSPENDED,
    VP8_STATUS_USER_ABORT,
    VP8_STATUS_NOT_ENOUGH_DATA
  } VP8StatusCode;

  struct WebPData {
    const uint8_t* bytes;
    size_t size;
    ...;
  };
  typedef struct WebPData WebPData;

  struct WebPPicture;
  typedef struct WebPPicture WebPPicture;

  typedef int (*WebPWriterFunction)(const uint8_t* data, size_t data_size, const WebPPicture* picture);

  struct WebPPicture {
    int use_argb;
    int width;
    int height;
    WebPWriterFunction writer;
    void* custom_ptr;
    ...;
  };

  struct WebPRGBABuffer {
    uint8_t* rgba;
    int stride;
    size_t size;
  };
  typedef struct WebPRGBABuffer WebPRGBABuffer;

  struct WebPYUVABuffer {
    uint8_t* y, *u, *v, *a;
    int y_stride;
    int u_stride, v_stride;
    int a_stride;
    size_t y_size;
    size_t u_size, v_size;
    size_t a_size;
  };
  typedef struct WebPYUVABuffer WebPYUVABuffer;

  struct WebPBitstreamFeatures {
    int width;
    int height;
    int has_alpha;
    int has_animation;
    int format;
    ...;
  };
  typedef struct WebPBitstreamFeatures WebPBitstreamFeatures;

  struct WebPDecBuffer {
    WEBP_CSP_MODE colorspace;
    int width, height;
    int is_external_memory;
    union {
      WebPRGBABuffer RGBA;
      WebPYUVABuffer YUVA;
    } u;
    ...;
  };
  typedef struct WebPDecBuffer WebPDecBuffer;

  struct WebPDecoderOptions {
    int use_threads;
    ...;
  };
  typedef struct WebPDecoderOptions WebPDecoderOptions;

  struct WebPDecoderConfig {
    WebPBitstreamFeatures input;
    WebPDecBuffer output;
    WebPDecoderOptions options;
    ...;
  };
  typedef struct WebPDecoderConfig WebPDecoderConfig;

  struct WebPConfig {
    int lossless;
    float quality;
    ...;
  };
  typedef struct WebPConfig WebPConfig;

  struct WebPMemoryWriter {
    uint8_t* mem;
    size_t size;
    ...;
  };
  typedef struct WebPMemoryWriter WebPMemoryWriter;

  struct WebPAnimEncoderOptions {
    int minimize_size;
    int kmin;
    int kmax;
    int allow_mixed;
    int verbose;
    ...;
  };
  typedef struct WebPAnimEncoderOptions WebPAnimEncoderOptions;

  struct WebPAnimDecoderOptions {
    WEBP_CSP_MODE color_mode;
    int use_threads;
    ...;
  };
  typedef struct WebPAnimDecoderOptions WebPAnimDecoderOptions;

  struct WebPAnimInfo {
    uint32_t canvas_width;
    uint32_t canvas_height;
    uint32_t loop_count;
    uint32_t bgcolor;
    uint32_t frame_count;
    ...;
  };
  typedef struct WebPAnimInfo WebPAnimInfo;

  // Opaque objects
  typedef struct WebPMux WebPMux;
  typedef struct WebPAnimEncoder WebPAnimEncoder;
  typedef struct WebPAnimDecoder WebPAnimDecoder;

  int WebPPictureInit(WebPPicture* picture);
  int WebPPictureAlloc(WebPPicture* picture);
  int WebPPictureImportRGB(WebPPicture* picture, const uint8_t* rgb,
    int rgb_stride);
  int WebPPictureImportRGBA(WebPPicture* picture, const uint8_t* rgba,
    int rgba_stride);
  void WebPPictureFree(WebPPicture* picture);

  int WebPInitDecoderConfig(WebPDecoderConfig* config);
  VP8StatusCode WebPGetFeatures(const uint8_t* data, size_t data_size,
    WebPBitstreamFeatures* features);
  VP8StatusCode WebPDecode(const uint8_t* data, size_t data_size,
    WebPDecoderConfig* config);
  void WebPFreeDecBuffer(WebPDecBuffer* buffer);

  int WebPConfigPreset(WebPConfig* config, WebPPreset preset, float quality);
  int WebPValidateConfig(const WebPConfig* config);

  int WebPEncode(const WebPConfig* config, WebPPicture* picture);

  void WebPMemoryWriterInit(WebPMemoryWriter* writer);
  int WebPMemoryWrite(const uint8_t* data, size_t data_size,
    const WebPPicture* picture);
  void WebPMemoryWriterClear(WebPMemoryWriter* writer);

  void WebPFree(void* ptr);

  void WebPDataInit(WebPData* webp_data);
  void WebPDataClear(WebPData* webp_data);

  int WebPAnimEncoderOptionsInit(WebPAnimEncoderOptions* enc_options);
  WebPAnimEncoder* WebPAnimEncoderNew(int width, int height,
    const WebPAnimEncoderOptions* enc_options);
  int WebPAnimEncoderAdd(WebPAnimEncoder* enc, struct WebPPicture* frame,
    int timestamp_ms, const struct WebPConfig* config);
  int WebPAnimEncoderAssemble(WebPAnimEncoder* enc, WebPData* webp_data);
  void WebPAnimEncoderDelete(WebPAnimEncoder* enc);

  int WebPAnimDecoderOptionsInit(WebPAnimDecoderOptions* dec_options);
  WebPAnimDecoder* WebPAnimDecoderNew(const WebPData* webp_data,
    const WebPAnimDecoderOptions* dec_options);
  int WebPAnimDecoderGetInfo(const WebPAnimDecoder* dec, WebPAnimInfo* info);
  int WebPAnimDecoderHasMoreFrames(const WebPAnimDecoder* dec);
  int WebPAnimDecoderGetNext(WebPAnimDecoder* dec, uint8_t** buf, int* timestamp);
  void WebPAnimDecoderReset(WebPAnimDecoder* dec);
  void WebPAnimDecoderDelete(WebPAnimDecoder* dec);
""")

if __name__ == "__main__":
  ffibuilder.compile(verbose=True)
