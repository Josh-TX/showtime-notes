import captureWorkletUrl from './capture-worklet.js?url'
import { ws } from '../ws'

let seq = 0
let audioContext: AudioContext | null = null
let stream: MediaStream | null = null

export async function startCapture(): Promise<void> {
  stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, sampleRate: 48000, echoCancellation: false, noiseSuppression: false, autoGainControl: false },
  })
  audioContext = new AudioContext({ sampleRate: 48000 })
  await audioContext.audioWorklet.addModule(captureWorkletUrl)
  const source = audioContext.createMediaStreamSource(stream)
  const node = new AudioWorkletNode(audioContext, 'capture-processor')
  node.port.onmessage = (event: MessageEvent<Int16Array>) => {
    const pcm = event.data
    const message = new Uint8Array(8 + pcm.byteLength)
    new DataView(message.buffer).setUint32(0, seq++, true)
    new DataView(message.buffer).setUint32(4, performance.now() >>> 0, true)
    message.set(new Uint8Array(pcm.buffer), 8)
    ws.sendBinary(message.buffer)
  }
  source.connect(node)
}

export function stopCapture(): void {
  stream?.getTracks().forEach((track) => track.stop())
  audioContext?.close()
  stream = null
  audioContext = null
  seq = 0
}
