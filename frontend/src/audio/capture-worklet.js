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
    const input = inputs[0]
    const left = input?.[0]
    if (left) {
      const right = input.length > 1 ? input[1] : null
      for (let i = 0; i < left.length; i++) {
        const sample = right ? (left[i] + right[i]) / 2 : left[i]
        const clamped = Math.max(-1, Math.min(1, sample))
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
