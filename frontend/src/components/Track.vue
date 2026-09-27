<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'

const PIXELS_PER_SECOND = 60
const PEAKS_PER_SECOND = 20
const WAVEFORM_LANE_HEIGHT = 120
const WAVEFORM_HEIGHT = WAVEFORM_LANE_HEIGHT * 2
const NORMAL_BEAT_ALPHA = 0.08
const DOWNBEAT_ALPHA = 0.5
const BAR_OFFSET_PERCENT = 0.3

const store = useShowStore()

const containerEl = ref<HTMLDivElement | null>(null)
const waveCanvas = ref<HTMLCanvasElement | null>(null)
const confidenceCanvas = ref<HTMLCanvasElement | null>(null)

const viewportWidthPx = ref(400)
const viewportHeightPx = ref(200)
const autoScroll = ref(true)

const durationSeconds = computed(() => {
  const fromPeaks = (store.waveform?.peaks.vocals.length ?? 0) / PEAKS_PER_SECOND
  return store.selectedSong?.durationSeconds ?? fromPeaks
})
const canvasWidthPx = computed(() => Math.max(1, durationSeconds.value * PIXELS_PER_SECOND))
const startWidthPx = computed(() => Math.round(viewportWidthPx.value * BAR_OFFSET_PERCENT))
const endWidthPx = computed(() => Math.round(viewportWidthPx.value * (1 - BAR_OFFSET_PERCENT)))
const trackWidthPx = computed(() => startWidthPx.value + canvasWidthPx.value + endWidthPx.value)
const totalHeightPx = computed(() => viewportHeightPx.value)

const positionLeftPx = computed(() =>
  store.positionSeconds === null ? null : startWidthPx.value + store.positionSeconds * PIXELS_PER_SECOND,
)

function timeToLeft(seconds: number): number {
  return startWidthPx.value + seconds * PIXELS_PER_SECOND
}

function drawWaveform(): void {
  const canvas = waveCanvas.value
  const waveform = store.waveform
  if (!canvas || !waveform) return
  canvas.width = canvasWidthPx.value
  canvas.height = totalHeightPx.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // beats drawn first, full height, so the opaque waveform peaks paint over them
  const downbeatSet = new Set(waveform.downbeats)
  ctx.globalAlpha = NORMAL_BEAT_ALPHA
  ctx.fillStyle = '#e0c33e'
  for (const beat of waveform.beats) {
    if (downbeatSet.has(beat)) continue
    const x = Math.round(beat * PIXELS_PER_SECOND)
    ctx.fillRect(x, 0, 1, canvas.height)
  }
  ctx.globalAlpha = DOWNBEAT_ALPHA
  for (const beat of waveform.downbeats) {
    const x = Math.round(beat * PIXELS_PER_SECOND)
    ctx.fillRect(x, 0, 1, canvas.height)
  }
  ctx.globalAlpha = 1

  const half = WAVEFORM_LANE_HEIGHT / 2
  const vocalsCenter = half
  const novocalsCenter = WAVEFORM_LANE_HEIGHT + half
  const drawPeaks = (peaks: number[], center: number, color: string) => {
    ctx.fillStyle = color
    const step = PIXELS_PER_SECOND / PEAKS_PER_SECOND
    for (let i = 0; i < peaks.length; i++) {
      const h = Math.min(1, peaks[i]) * half
      const x = i * step
      ctx.fillRect(x, center - h, Math.max(1, step), Math.max(1, h * 2))
    }
  }
  drawPeaks(waveform.peaks.vocals, vocalsCenter, '#4a9eff')
  drawPeaks(waveform.peaks.novocals, novocalsCenter, '#7a7a7a')
}

function drawConfidenceOverlay(): void {
  const canvas = confidenceCanvas.value
  const container = containerEl.value
  if (!canvas || !container) return
  const width = viewportWidthPx.value
  const height = totalHeightPx.value
  if (canvas.width !== width) canvas.width = width
  if (canvas.height !== height) canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, width, height)
  if (!store.confidenceBars.length) return

  const step = PIXELS_PER_SECOND / PEAKS_PER_SECOND
  const originX = startWidthPx.value - container.scrollLeft
  for (const bar of store.confidenceBars) {
    const x = originX + bar.refSeconds * PIXELS_PER_SECOND
    if (x + step < 0 || x > width) continue
    const alpha = Math.max(0, Math.min(1, bar.score))
    ctx.fillStyle = `rgba(224, 195, 62, ${alpha * 0.6})`
    ctx.fillRect(x, 0, Math.max(1, step), height)
  }
}

function refreshLayout(): void {
  viewportWidthPx.value = containerEl.value?.clientWidth ?? 400
  viewportHeightPx.value = containerEl.value?.clientHeight ?? 200
  drawWaveform()
  drawConfidenceOverlay()
}

function onTrackDoubleClick(event: MouseEvent): void {
  if (!store.selectedSong) return
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const x = event.clientX - rect.left - startWidthPx.value
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
watch(() => store.confidenceBars, drawConfidenceOverlay)
watch(
  () => store.positionSeconds,
  (seconds) => {
    if (!autoScroll.value || seconds === null || !containerEl.value) return
    containerEl.value.scrollLeft = seconds * PIXELS_PER_SECOND
  },
)

let resizeObserver: ResizeObserver | undefined
onMounted(() => {
  refreshLayout()
  resizeObserver = new ResizeObserver(refreshLayout)
  if (containerEl.value) resizeObserver.observe(containerEl.value)
})
onUnmounted(() => resizeObserver?.disconnect())
</script>

<template>
  <div class="track-wrap">
    <div class="track-toolbar">
      <label><input type="checkbox" v-model="autoScroll" /> auto-scroll</label>
    </div>
    <div class="track-outer">
      <div class="track-container" ref="containerEl" @scroll="drawConfidenceOverlay">
        <div
          v-if="store.selectedSong"
          class="track"
          :style="{ width: `${trackWidthPx}px` }"
          @dblclick="onTrackDoubleClick"
        >
          <div class="start-area" :style="{ width: `${startWidthPx}px` }"></div>
          <canvas ref="waveCanvas" class="wave-canvas" :style="{ width: `${canvasWidthPx}px`, height: `${totalHeightPx}px` }" />
          <div class="end-area" :style="{ width: `${endWidthPx}px` }"></div>
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
      <canvas
        ref="confidenceCanvas"
        class="confidence-overlay"
        :style="{ width: `${viewportWidthPx}px`, height: `${totalHeightPx}px` }"
      />
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
.track-outer {
  position: relative;
  flex: 1;
  overflow: hidden;
}
.track-container {
  width: 100%;
  height: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  position: relative;
}
.track {
  position: relative;
  display: flex;
  height: 100%;
}
.start-area,
.end-area {
  flex: none;
  height: 100%;
  background: #14161a;
}
.wave-canvas {
  flex: none;
  display: block;
}
.confidence-overlay {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  z-index: 2;
}
.position-bar {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #ff3b3b;
  z-index: 3;
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
  z-index: 4;
}
</style>
