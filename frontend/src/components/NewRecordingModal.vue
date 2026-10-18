<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'
import { ws } from '../ws'
import { shape } from './timelineDraw'

const WINDOW_SECONDS = 12
const CLOCK_TICK_MS = 100
const MAX_PEAK_SECONDS = 13
const OFFSETS = Array.from({ length: WINDOW_SECONDS }, (_, i) => WINDOW_SECONDS - i)
const MARKER_STEP_SECONDS = 2

const store = useShowStore()
const dialog = ref<HTMLDialogElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const name = ref('')
const starting = ref(false)
const nowMs = ref(Date.now())
const hoveredAgo = ref<number | null>(null)

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

  ctx.strokeStyle = '#2a2a30'
  ctx.lineWidth = 1
  for (let i = 1; i < WINDOW_SECONDS; i += MARKER_STEP_SECONDS) {
    const x = Math.round((i / WINDOW_SECONDS) * w) + 0.5
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, h - labelH)
    ctx.stroke()
  }

  ctx.strokeStyle = '#555'
  ctx.fillStyle = '#aaa'
  ctx.font = '11px sans-serif'
  ctx.lineWidth = 1
  ctx.textBaseline = 'bottom'
  for (let i = 0; i <= WINDOW_SECONDS; i += MARKER_STEP_SECONDS) {
    const x = Math.min(w - 0.5, Math.max(0.5, (i / WINDOW_SECONDS) * w))
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, h - labelH)
    ctx.stroke()
    ctx.textAlign = i === 0 ? 'left' : i === WINDOW_SECONDS ? 'right' : 'center'
    ctx.fillText(i === WINDOW_SECONDS ? 'now' : `${WINDOW_SECONDS - i}s ago`, x + (i === 0 ? 2 : i === WINDOW_SECONDS ? -2 : 0), h)
  }

  if (hoveredAgo.value !== null) {
    const x = Math.min(w - 1, Math.max(1, ((WINDOW_SECONDS - hoveredAgo.value) / WINDOW_SECONDS) * w))
    ctx.strokeStyle = '#4da3ff'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, h - labelH)
    ctx.stroke()
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
    <div class="modal-header">
      <h2>New Recording</h2>
      <button class="close-btn" aria-label="Close" @click="closeModal">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M5 5L19 19M19 5L5 19" />
        </svg>
      </button>
    </div>
    <div class="modal-content">
      <div class="name-field">
        <label for="recording-name">Song name</label>
        <input id="recording-name" v-model="name" class="name-input" />
      </div>
      <p v-if="blockedMessage" class="blocked">{{ blockedMessage }}</p>
      <canvas ref="canvas" class="meter" />
      <div class="ago-buttons">
        <button
          v-for="s in OFFSETS"
          :key="s"
          :disabled="!canStartAgo(s)"
          @click="start(s)"
          @mouseenter="hoveredAgo = s"
          @mouseleave="hoveredAgo = null"
          @focus="hoveredAgo = s"
          @blur="hoveredAgo = null"
        >
          <span class="num">{{ s }}</span>
          <span>seconds</span>
          <span>ago</span>
        </button>
      </div>
      <p class="ago-hint">Click one of the above buttons to start recording at that point</p>
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
  max-width: 960px;
  width: 90vw;
}
.recording-modal::backdrop {
  background: rgba(0, 0, 0, 0.6);
}
.modal-header {
  background: #141416;
  padding: 0.75rem 1.25rem;
  border-radius: 8px 8px 0 0;
  border-bottom: 1px solid #333;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.close-btn {
  background: none;
  border: none;
  color: #aaa;
  padding: 0.2rem;
  display: flex;
  cursor: pointer;
}
.close-btn:hover {
  color: #fff;
}
.modal-content {
  background: #141416;
  color: inherit;
  padding: 1.25rem;
  border-radius: 0 0 8px 8px;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.modal-header h2 {
  margin: 0;
  font-size: 1.2rem;
}
.name-field {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.name-field label {
  font-size: 0.9rem;
  color: #aaa;
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
  grid-template-columns: repeat(12, 1fr);
  gap: 0;
}
.ago-buttons button {
  margin: 0 1px;
  font-size: 0.65rem;
  line-height: 1.1;
  padding: 0.3rem 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.ago-buttons button {
  background: #1c1c20;
  color: #ddd;
  border: 1px solid #333;
  border-radius: 4px;
  cursor: pointer;
}
.ago-buttons button:hover:not(:disabled),
.ago-buttons button:focus-visible:not(:disabled) {
  border-color: #4da3ff;
  box-shadow: 0 0 0 1px #4da3ff;
  outline: none;
}
.ago-buttons button:disabled {
  opacity: 0.4;
  cursor: default;
}
.ago-buttons .num {
  font-size: 1.6rem;
  font-weight: 600;
}
.ago-hint {
  margin: 0;
  text-align: center;
  color: #aaa;
  font-size: 0.9rem;
}
.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.4rem;
}
</style>
