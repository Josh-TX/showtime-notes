<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useShowStore } from '../store/show'

const PIXELS_PER_SECOND = 60
const LIVE_PEAKS_PER_SECOND = 20
const TIMELINE_HEIGHT = 160
const LIVE_ALIGN_FRACTION = 0.75

const store = useShowStore()

const containerEl = ref<HTMLDivElement | null>(null)
const waveCanvas = ref<HTMLCanvasElement | null>(null)

const leftPaddingPx = ref(400)
const autoScroll = ref(true)

const elapsedSeconds = computed(() => store.recordingPeaks.length / LIVE_PEAKS_PER_SECOND)
const timelineWidthPx = computed(() => Math.max(1, elapsedSeconds.value * PIXELS_PER_SECOND))
const timelineTotalWidthPx = computed(() => leftPaddingPx.value + timelineWidthPx.value)
const liveEdgeLeftPx = computed(() => leftPaddingPx.value + timelineWidthPx.value)

function formatElapsed(seconds: number): string {
  const total = Math.floor(seconds)
  const mm = Math.floor(total / 60)
  const ss = total % 60
  return `${mm}:${ss.toString().padStart(2, '0')}`
}

function resizePadding(): void {
  leftPaddingPx.value = (containerEl.value?.clientWidth ?? 400) * LIVE_ALIGN_FRACTION
  drawWaveform()
  scrollToLive()
}

function drawWaveform(): void {
  const canvas = waveCanvas.value
  if (!canvas) return
  canvas.width = timelineWidthPx.value
  canvas.height = TIMELINE_HEIGHT
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const mid = TIMELINE_HEIGHT / 2
  const step = PIXELS_PER_SECOND / LIVE_PEAKS_PER_SECOND
  ctx.fillStyle = '#4a9eff'
  const peaks = store.recordingPeaks
  for (let i = 0; i < peaks.length; i++) {
    const h = Math.min(1, peaks[i]) * mid
    const x = i * step
    ctx.fillRect(x, mid - h, Math.max(1, step), h * 2)
  }

  ctx.strokeStyle = '#333'
  ctx.beginPath()
  ctx.moveTo(0, mid)
  ctx.lineTo(canvas.width, mid)
  ctx.stroke()
}

function scrollToLive(): void {
  if (!autoScroll.value || !containerEl.value) return
  containerEl.value.scrollLeft = liveEdgeLeftPx.value - containerEl.value.clientWidth * LIVE_ALIGN_FRACTION
}

watch(() => store.recordingPeaks.length, () => {
  nextTick(drawWaveform)
  scrollToLive()
})

let resizeObserver: ResizeObserver | undefined
onMounted(() => {
  resizePadding()
  resizeObserver = new ResizeObserver(resizePadding)
  if (containerEl.value) resizeObserver.observe(containerEl.value)
})
onUnmounted(() => resizeObserver?.disconnect())
</script>

<template>
  <div class="timeline-wrap">
    <div class="timeline-toolbar">
      <label><input type="checkbox" v-model="autoScroll" /> follow live</label>
      <span class="elapsed">{{ formatElapsed(elapsedSeconds) }}</span>
    </div>
    <div class="timeline-container" ref="containerEl">
      <div class="timeline" :style="{ width: `${timelineTotalWidthPx}px`, height: `${TIMELINE_HEIGHT}px` }">
        <canvas ref="waveCanvas" class="wave-canvas" :style="{ left: `${leftPaddingPx}px` }" />
        <div class="live-edge" :style="{ left: `${liveEdgeLeftPx}px` }" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.timeline-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.timeline-toolbar {
  padding: 0.2rem 0.6rem;
  font-size: 0.8rem;
  border-bottom: 1px solid #2a2a2a;
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.elapsed {
  font-family: monospace;
  color: #ccc;
}
.timeline-container {
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
  position: relative;
}
.timeline {
  position: relative;
}
.wave-canvas {
  position: absolute;
  top: 0;
}
.live-edge {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #e04040;
}
</style>
