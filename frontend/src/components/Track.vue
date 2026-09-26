<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'

const PIXELS_PER_SECOND = 60
const PEAKS_PER_SECOND = 20
const TRACK_HEIGHT = 160
const AUTO_SCROLL_ALIGN_FRACTION = 0.3

const store = useShowStore()

const containerEl = ref<HTMLDivElement | null>(null)
const waveCanvas = ref<HTMLCanvasElement | null>(null)
const barsCanvas = ref<HTMLCanvasElement | null>(null)

const paddingPx = ref(400)
const autoScroll = ref(true)

const durationSeconds = computed(() => {
  const fromPeaks = (store.waveform?.peaks.vocals.length ?? 0) / PEAKS_PER_SECOND
  return store.selectedSong?.durationSeconds ?? fromPeaks
})
const trackWidthPx = computed(() => Math.max(1, durationSeconds.value * PIXELS_PER_SECOND))
const trackTotalWidthPx = computed(() => paddingPx.value * 2 + trackWidthPx.value)

const positionLeftPx = computed(() =>
  store.positionSeconds === null ? null : paddingPx.value + store.positionSeconds * PIXELS_PER_SECOND,
)

function timeToLeft(seconds: number): number {
  return paddingPx.value + seconds * PIXELS_PER_SECOND
}

function resizePadding(): void {
  paddingPx.value = containerEl.value?.clientWidth ?? 400
  drawWaveform()
}

function drawWaveform(): void {
  const canvas = waveCanvas.value
  const waveform = store.waveform
  if (!canvas || !waveform) return
  canvas.width = trackWidthPx.value
  canvas.height = TRACK_HEIGHT
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const mid = TRACK_HEIGHT / 2
  const half = mid
  const drawPeaks = (peaks: number[], baseline: number, up: boolean, color: string) => {
    ctx.fillStyle = color
    const step = PIXELS_PER_SECOND / PEAKS_PER_SECOND
    for (let i = 0; i < peaks.length; i++) {
      const h = Math.min(1, peaks[i]) * half
      const x = i * step
      ctx.fillRect(x, up ? baseline - h : baseline, Math.max(1, step), h)
    }
  }
  drawPeaks(waveform.peaks.vocals, mid, true, '#4a9eff')
  drawPeaks(waveform.peaks.novocals, mid, false, '#7a7a7a')

  ctx.strokeStyle = '#333'
  ctx.beginPath()
  ctx.moveTo(0, mid)
  ctx.lineTo(canvas.width, mid)
  ctx.stroke()

  for (const beat of waveform.downbeats) {
    ctx.strokeStyle = '#e0c33e'
    ctx.beginPath()
    ctx.moveTo(beat * PIXELS_PER_SECOND, 0)
    ctx.lineTo(beat * PIXELS_PER_SECOND, TRACK_HEIGHT)
    ctx.stroke()
  }
  ctx.strokeStyle = '#555'
  for (const beat of waveform.beats) {
    if (waveform.downbeats.includes(beat)) continue
    ctx.beginPath()
    ctx.moveTo(beat * PIXELS_PER_SECOND, TRACK_HEIGHT - 10)
    ctx.lineTo(beat * PIXELS_PER_SECOND, TRACK_HEIGHT)
    ctx.stroke()
  }
}

function drawConfidenceBars(): void {
  const canvas = barsCanvas.value
  if (!canvas) return
  canvas.width = trackWidthPx.value
  canvas.height = TRACK_HEIGHT
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  if (!store.confidenceBars.length) return
  const step = PIXELS_PER_SECOND / PEAKS_PER_SECOND
  for (const bar of store.confidenceBars) {
    const alpha = Math.max(0, Math.min(1, bar.score))
    ctx.fillStyle = `rgba(224, 195, 62, ${alpha * 0.6})`
    ctx.fillRect(bar.refSeconds * PIXELS_PER_SECOND, 0, Math.max(1, step), TRACK_HEIGHT)
  }
}

function onTrackDoubleClick(event: MouseEvent): void {
  if (!store.selectedSong) return
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const x = event.clientX - rect.left - paddingPx.value
  const seconds = Math.max(0, x / PIXELS_PER_SECOND)
  const text = window.prompt('Track note text:')
  if (text) api.addTrackNote(store.selectedSong.id, seconds, text)
}

function editNote(noteId: string, currentText: string): void {
  if (!store.selectedSong) return
  const text = window.prompt('Edit note (empty to delete):', currentText)
  if (text === null) return
  if (text === '') {
    api.deleteTrackNote(store.selectedSong.id, noteId)
  } else {
    api.updateTrackNote(store.selectedSong.id, noteId, { text })
  }
}

watch(() => store.waveform, () => nextTick(drawWaveform))
watch(() => store.confidenceBars, drawConfidenceBars)
watch(
  () => store.positionSeconds,
  (seconds) => {
    if (!autoScroll.value || seconds === null || !containerEl.value) return
    containerEl.value.scrollLeft = timeToLeft(seconds) - containerEl.value.clientWidth * AUTO_SCROLL_ALIGN_FRACTION
  },
)

let resizeObserver: ResizeObserver | undefined
onMounted(() => {
  resizePadding()
  resizeObserver = new ResizeObserver(resizePadding)
  if (containerEl.value) resizeObserver.observe(containerEl.value)
})
onUnmounted(() => resizeObserver?.disconnect())
</script>

<template>
  <div class="track-wrap">
    <div class="track-toolbar">
      <label><input type="checkbox" v-model="autoScroll" /> auto-scroll</label>
    </div>
    <div class="track-container" ref="containerEl">
      <div
        v-if="store.selectedSong"
        class="track"
        :style="{ width: `${trackTotalWidthPx}px`, height: `${TRACK_HEIGHT}px` }"
        @dblclick="onTrackDoubleClick"
      >
        <canvas ref="waveCanvas" class="wave-canvas" :style="{ left: `${paddingPx}px` }" />
        <canvas ref="barsCanvas" class="bars-canvas" :style="{ left: `${paddingPx}px` }" />
        <div
          v-for="note in store.selectedSong.trackNotes"
          :key="note.id"
          class="track-note"
          :style="{ left: `${timeToLeft(note.timeSeconds)}px` }"
          @click="editNote(note.id, note.text)"
        >
          {{ note.text }}
        </div>
        <div v-if="positionLeftPx !== null" class="position-bar" :style="{ left: `${positionLeftPx}px` }" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.track-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.track-toolbar {
  padding: 0.2rem 0.6rem;
  font-size: 0.8rem;
  border-bottom: 1px solid #2a2a2a;
}
.track-container {
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
  position: relative;
}
.track {
  position: relative;
}
.wave-canvas,
.bars-canvas {
  position: absolute;
  top: 0;
}
.bars-canvas {
  pointer-events: none;
}
.position-bar {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #ff3b3b;
}
.track-note {
  position: absolute;
  top: 4px;
  transform: translateX(-50%);
  background: #333;
  border: 1px solid #555;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 0.7rem;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  z-index: 5;
}
</style>
