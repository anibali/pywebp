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
