<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'
import { ws } from '../ws'

const WINDOW_SECONDS = 3
const CLOCK_TICK_MS = 100
const MAX_PEAK_SECONDS = 5
// Subtle fixed contrast (stateless, so bars never change once drawn): levels under FLOOR are flat, the rest is
// rescaled and curved so quiet stays quiet. Much gentler than the recording timeline's adaptive stretch.
const LEVEL_FLOOR = 0.35
const LEVEL_CURVE = 2
function shape(level: number): number {
  return Math.max(0, (level - LEVEL_FLOOR) / (1 - LEVEL_FLOOR)) ** LEVEL_CURVE
}
const OFFSETS = [3, 2, 1]
const MARKER_LABELS = ['3s ago', '2s ago', '1s ago', 'now']

const store = useShowStore()
const dialog = ref<HTMLDialogElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const name = ref('')
const starting = ref(false)
const nowMs = ref(Date.now())

interface Preview {
  endTsMs: number
  endPeakIndex: number
  peaksPerSecond: number
  peaks: number[]
}
// loaded from the API on open, then extended by 'recording_preview' ws messages (only sent while subscribed)
const preview = shallowRef<Preview | null>(null)
let pendingMessages: Preview[] = []
let isOpen = false
let clockTimer: number | undefined
let rafId = 0

const hasListener = computed(() => !!store.show?.listener.deviceName)
const isRecording = computed(() => !!store.show?.songs.some((s) => s.status === 'recording'))
const blockedMessage = computed(() => {
  if (!hasListener.value) return "server has no listener and can't record"
  if (isRecording.value) return 'A recording is already in progress and must be stopped before starting a new one'
  return null
})
const canStart = computed(() => !blockedMessage.value && !starting.value)

// seconds of audio currently buffered, as of nowMs; the "N seconds ago" button needs N of them
const bufferedSeconds = computed(() => {
  const p = preview.value
  if (!p) return 0
  return p.peaks.length / p.peaksPerSecond - (nowMs.value - p.endTsMs) / 1000
})
function canStartAgo(seconds: number): boolean {
  return canStart.value && bufferedSeconds.value >= seconds
}

async function load(): Promise<void> {
  pendingMessages = []
  preview.value = null
  try {
    const loaded = await api.getRecordingPreview()
    if (!isOpen) return
    preview.value = loaded
    const queued = pendingMessages
    pendingMessages = []
    queued.forEach(applyMessage)
  } catch (err) {
    console.error(err)
  }
}

// Appends the message's windows that the preview doesn't have yet; reloads if a gap shows messages were missed.
function applyMessage(msg: Preview): void {
  const cur = preview.value
  if (!cur) {
    pendingMessages.push(msg)
    return
  }
  const firstIndex = msg.endPeakIndex - msg.peaks.length + 1
  const skip = Math.max(0, cur.endPeakIndex + 1 - firstIndex)
  if (skip >= msg.peaks.length) return
  if (firstIndex + skip > cur.endPeakIndex + 1) {
    load()
    return
  }
  const peaks = cur.peaks.concat(msg.peaks.slice(skip))
  preview.value = {
    endTsMs: msg.endTsMs,
    endPeakIndex: msg.endPeakIndex,
    peaksPerSecond: cur.peaksPerSecond,
    peaks: peaks.slice(-MAX_PEAK_SECONDS * cur.peaksPerSecond),
  }
}

function subscribe(): void {
  ws.send('set_recording_preview_subscription', { wanted: true })
  load()
}

// the socket reconnecting drops the server-side subscription
watch(
  () => store.connected,
  (connected) => {
    if (connected && isOpen) subscribe()
  },
)

function draw(): void {
  rafId = requestAnimationFrame(draw)
  const el = canvas.value
  if (!el) return
  const dpr = window.devicePixelRatio || 1
  const w = el.clientWidth
  const h = el.clientHeight
  if (el.width !== Math.round(w * dpr) || el.height !== Math.round(h * dpr)) {
    el.width = Math.round(w * dpr)
    el.height = Math.round(h * dpr)
  }
  const ctx = el.getContext('2d')!
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, w, h)

  const labelH = 16
  const barsH = h - labelH
  const now = Date.now()
  const lo = now - WINDOW_SECONDS * 1000
  const xOf = (t: number) => ((t - lo) / (WINDOW_SECONDS * 1000)) * w

  const p = preview.value
  if (p && p.peaks.length > 0) {
    const { endTsMs, peaksPerSecond, peaks } = p
    const stepMs = 1000 / peaksPerSecond
    ctx.fillStyle = '#4d4d5a'
    for (let k = 0; k < peaks.length; k++) {
      const t0 = endTsMs - (peaks.length - k) * stepMs
      const x0 = xOf(t0)
      const x1 = xOf(t0 + stepMs)
      if (x1 < 0 || x0 > w) continue
      const barH = Math.max(1, shape(peaks[k]) * barsH)
      ctx.fillRect(x0, (barsH - barH) / 2, Math.max(1, x1 - x0), barH)
    }
  }

  ctx.strokeStyle = '#555'
  ctx.fillStyle = '#aaa'
  ctx.font = '11px sans-serif'
  ctx.lineWidth = 1
  ctx.textBaseline = 'bottom'
  for (let i = 0; i <= WINDOW_SECONDS; i++) {
    const x = Math.min(w - 0.5, Math.max(0.5, (i / WINDOW_SECONDS) * w))
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, h - labelH)
    ctx.stroke()
    ctx.textAlign = i === 0 ? 'left' : i === WINDOW_SECONDS ? 'right' : 'center'
    ctx.fillText(MARKER_LABELS[i], x + (i === 0 ? 2 : i === WINDOW_SECONDS ? -2 : 0), h)
  }
}

function openModal(): void {
  name.value = ''
  starting.value = false
  isOpen = true
  dialog.value?.showModal()
  ws.on('recording_preview', applyMessage)
  subscribe()
  clockTimer = window.setInterval(() => (nowMs.value = Date.now()), CLOCK_TICK_MS)
  rafId = requestAnimationFrame(draw)
}
function closeModal(): void {
  dialog.value?.close()
}
function onDialogClose(): void {
  if (isOpen) ws.send('set_recording_preview_subscription', { wanted: false })
  isOpen = false
  ws.off('recording_preview', applyMessage)
  window.clearInterval(clockTimer)
  cancelAnimationFrame(rafId)
}
onBeforeUnmount(onDialogClose)

async function start(offsetSeconds: number): Promise<void> {
  if (!canStart.value) return
  const clickTsMs = Date.now()
  starting.value = true
  try {
    const song = await api.startRecording(name.value.trim(), clickTsMs, offsetSeconds)
    closeModal()
    await store.selectSong(song.id)
  } catch (err) {
    console.error(err)
  } finally {
    starting.value = false
  }
}
</script>

<template>
  <button @click="openModal">New Recording</button>

  <dialog ref="dialog" class="recording-modal" @click.self="closeModal" @close="onDialogClose">
    <div class="modal-content">
      <h2>New Recording</h2>
      <input v-model="name" class="name-input" placeholder="Song Name" />
      <p v-if="blockedMessage" class="blocked">{{ blockedMessage }}</p>
      <canvas ref="canvas" class="meter" />
      <div class="ago-buttons">
        <button v-for="s in OFFSETS" :key="s" :disabled="!canStartAgo(s)" @click="start(s)">
          Start Recording {{ s }} second{{ s === 1 ? '' : 's' }} ago
        </button>
      </div>
      <div class="modal-footer">
        <button @click="closeModal">Cancel</button>
        <button :disabled="!canStart" @click="start(0)">Start Recording Now</button>
      </div>
    </div>
  </dialog>
</template>

<style scoped>
.recording-modal {
  border: none;
  border-radius: 8px;
  padding: 0;
  background: transparent;
  max-width: 760px;
  width: 90vw;
}
.recording-modal::backdrop {
  background: rgba(0, 0, 0, 0.6);
}
.modal-content {
  background: #1e1e1e;
  color: inherit;
  padding: 1.25rem;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.modal-content h2 {
  margin: 0;
}
.name-input {
  font-size: 1.1rem;
  background: #1c1c1c;
  color: inherit;
  border: 1px solid #333;
  padding: 0.3rem 0.5rem;
}
.blocked {
  margin: 0;
  color: #e0c33e;
  font-size: 1.1rem;
  font-weight: 600;
}
.meter {
  width: 100%;
  height: 240px;
  background: #050506;
  outline: 1px solid #333;
  display: block;
}
.ago-buttons {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
}
.ago-buttons button {
  margin: 0 2px;
  font-size: 0.8rem;
  padding: 0.3rem 0.2rem;
}
.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.4rem;
}
</style>
