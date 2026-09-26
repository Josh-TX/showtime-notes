// AudioWorkletProcessor: buffers mono float samples into 960-sample (20ms @ 48kHz) Int16 chunks and posts each
// completed chunk to the main thread.
const CHUNK_SAMPLES = 960

class CaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.buffer = new Int16Array(CHUNK_SAMPLES)
    this.offset = 0
  }

  process(inputs) {
    const channel = inputs[0]?.[0]
    if (channel) {
      for (let i = 0; i < channel.length; i++) {
        const clamped = Math.max(-1, Math.min(1, channel[i]))
        this.buffer[this.offset++] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff
        if (this.offset === CHUNK_SAMPLES) {
          this.port.postMessage(this.buffer.slice())
          this.offset = 0
        }
      }
    }
    return true
  }
}

registerProcessor('capture-processor', CaptureProcessor)
