import captureWorkletUrl from './capture-worklet.js?url'
import { reactive } from 'vue'
import { ws } from '../ws'

export const captureState = reactive<{ kind: 'mic' | 'tab' | null }>({ kind: null })

let seq = 0
let gainNode: GainNode | null = null
let gainDb = 0
let audioContext: AudioContext | null = null
let stream: MediaStream | null = null

async function pipeStream(mediaStream: MediaStream): Promise<void> {
  stream = mediaStream
  audioContext = new AudioContext({ sampleRate: 48000 })
  await audioContext.audioWorklet.addModule(captureWorkletUrl)
  const source = audioContext.createMediaStreamSource(stream)
  const node = new AudioWorkletNode(audioContext, 'capture-processor', {
    channelCount: 2,
    channelCountMode: 'explicit',
    channelInterpretation: 'discrete',
  })
  node.port.onmessage = (event: MessageEvent<Int16Array>) => {
    const pcm = event.data
    const message = new Uint8Array(8 + pcm.byteLength)
    new DataView(message.buffer).setUint32(0, seq++, true)
    new DataView(message.buffer).setUint32(4, performance.now() >>> 0, true)
    message.set(new Uint8Array(pcm.buffer), 8)
    ws.sendBinary(message.buffer)
  }
  gainNode = audioContext.createGain()
  gainNode.gain.value = dbToLinear(gainDb)
  source.connect(gainNode).connect(node)
}

const dbToLinear = (db: number) => 10 ** (db / 20)

// The server's input gain setting; applied to the listener's audio before it's converted to int16 and streamed.
export function setCaptureGainDb(db: number): void {
  gainDb = db
  if (gainNode) gainNode.gain.value = dbToLinear(db)
}

export async function startCapture(deviceId?: string): Promise<void> {
  const mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      sampleRate: 48000,
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
      ...(deviceId ? { deviceId: { exact: deviceId } } : {}),
    },
  })
  await pipeStream(mediaStream)
  captureState.kind = 'mic'
}

export async function startTabCapture(): Promise<void> {
  const displayStream = await navigator.mediaDevices.getDisplayMedia({
    video: true,
    audio: {
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
    },
  })
  const audioTracks = displayStream.getAudioTracks()
  displayStream.getVideoTracks().forEach((track) => track.stop())
  if (audioTracks.length === 0) {
    throw new Error('The shared tab did not include audio. Re-share and check "Share tab audio".')
  }
  await pipeStream(new MediaStream(audioTracks))
  captureState.kind = 'tab'
}

export function stopCapture(): void {
  stream?.getTracks().forEach((track) => track.stop())
  audioContext?.close()
  stream = null
  audioContext = null
  gainNode = null
  seq = 0
  captureState.kind = null
}

export function getCaptureDeviceId(): string | undefined {
  return stream?.getAudioTracks()[0]?.getSettings().deviceId
}
