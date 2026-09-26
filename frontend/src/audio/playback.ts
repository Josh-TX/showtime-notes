import playbackWorkletUrl from './playback-worklet.js?url'

let audioContext: AudioContext | null = null
let node: AudioWorkletNode | null = null

export async function startPlayback(): Promise<void> {
  audioContext = new AudioContext({ sampleRate: 48000 })
  await audioContext.audioWorklet.addModule(playbackWorkletUrl)
  node = new AudioWorkletNode(audioContext, 'playback-processor')
  node.connect(audioContext.destination)
}

export function pushPlaybackChunk(data: ArrayBuffer): void {
  if (!node || data.byteLength <= 8) return
  const pcm = new Int16Array(data.slice(8))
  const floats = new Float32Array(pcm.length)
  for (let i = 0; i < pcm.length; i++) floats[i] = pcm[i] / 32768
  node.port.postMessage(floats, [floats.buffer])
}

export function stopPlayback(): void {
  node?.disconnect()
  audioContext?.close()
  node = null
  audioContext = null
}
