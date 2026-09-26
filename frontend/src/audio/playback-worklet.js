// AudioWorkletProcessor: a small ring buffer fed by float32 chunks posted from the main thread. Underrun plays
// silence; overflow drops the oldest samples still in the ring.
class PlaybackProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.capacity = sampleRate * 2 // 2s ring
    this.ring = new Float32Array(this.capacity)
    this.writeIdx = 0
    this.readIdx = 0
    this.available = 0
    this.port.onmessage = (event) => {
      const samples = event.data
      for (let i = 0; i < samples.length; i++) {
        this.ring[this.writeIdx] = samples[i]
        this.writeIdx = (this.writeIdx + 1) % this.capacity
        if (this.available < this.capacity) {
          this.available++
        } else {
          this.readIdx = (this.readIdx + 1) % this.capacity
        }
      }
    }
  }

  process(_inputs, outputs) {
    const output = outputs[0][0]
    for (let i = 0; i < output.length; i++) {
      if (this.available > 0) {
        output[i] = this.ring[this.readIdx]
        this.readIdx = (this.readIdx + 1) % this.capacity
        this.available--
      } else {
        output[i] = 0
      }
    }
    return true
  }
}

registerProcessor('playback-processor', PlaybackProcessor)
