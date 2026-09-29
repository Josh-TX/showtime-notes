<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'
import { clientSettings } from '../store/clientSettings'
import { PositionSmoother, type BarState } from './smoothing'

const PEAKS_PER_SECOND = 20
const WAVEFORM_LANE_HEIGHT = 120
const NORMAL_BEAT_ALPHA = 0.08
const DOWNBEAT_ALPHA = 0.25
const WAVEFORM_ALPHA = 0.5
const CONFIDENCE_BAR_ALPHA = 0.7
const CONFIDENCE_BAR_BG_ALPHA = 0.03
const CONFIDENCE_BAR_MAX_HEIGHT = 120
const ACQUIRING_BAR_COLOR = '#e0c33e'
const TRACKING_BAR_COLOR = '#3ecf5f'
// Rank order (best candidate first) maps to these colors; shared with CandidatesPanel.vue's color key.
const CANDIDATE_COLORS = ['#00e5ff', '#ff00ff', '#ff9800']

const store = useShowStore()

const containerEl = ref<HTMLDivElement | null>(null)
const waveCanvas = ref<HTMLCanvasElement | null>(null)
const acquiringBarsCanvas = ref<HTMLCanvasElement | null>(null)
const trackingBarsCanvas = ref<HTMLCanvasElement | null>(null)

const viewportWidthPx = ref(400)
const viewportHeightPx = ref(200)
const autoScroll = ref(true)
const displayPosition = ref<number | null>(null)
const positionBars = ref<BarState[]>([])
const smoother = new PositionSmoother()
// ref-seconds at local x=0 of trackingBarsCanvas, from whichever bars snapshot is currently drawn into it
const trackingBarsOriginSeconds = ref<number | null>(null)

// Timeline width setting = seconds visible across the container, so zoom follows the container width.
const pixelsPerSecond = computed(() => viewportWidthPx.value / clientSettings.timelineWidthSeconds)
const barOffsetFraction = computed(() => clientSettings.autoScrollLeftOffsetPercent / 100)

const durationSeconds = computed(() => {
  const fromPeaks = (store.waveform?.peaks.vocals.length ?? 0) / PEAKS_PER_SECOND
  return store.selectedSong?.durationSeconds ?? fromPeaks
})
const canvasWidthPx = computed(() => Math.max(1, durationSeconds.value * pixelsPerSecond.value))
const startWidthPx = computed(() => Math.round(viewportWidthPx.value * barOffsetFraction.value))
const endWidthPx = computed(() => Math.round(viewportWidthPx.value * (1 - barOffsetFraction.value)))
const timelineWidthPx = computed(() => startWidthPx.value + canvasWidthPx.value + endWidthPx.value)
const totalHeightPx = computed(() => viewportHeightPx.value)

function positionToLeft(position: number): number {
  return startWidthPx.value + position * pixelsPerSecond.value
}

const barStepPx = computed(() => pixelsPerSecond.value / PEAKS_PER_SECOND)
const trackingBarsWidthPx = computed(() => Math.max(1, store.confidenceBars.length * barStepPx.value))
// Mirrors positionLeftPx's anchor extrapolation, offset by where the drawn window's first bar sits relative to
// the anchor - so the window glides in lockstep with the position bar instead of jumping on every new snapshot.
const trackingBarsLeftPx = computed(() => {
  const anchor = store.positionAnchor
  if (anchor === null || trackingBarsOriginSeconds.value === null || displayPosition.value === null) return null
  const drift = displayPosition.value - anchor.refSeconds
  return startWidthPx.value + (trackingBarsOriginSeconds.value + drift) * pixelsPerSecond.value
})

// Acquiring bars are anchors too ("live-now is at this ref time"), so between snapshots they glide right
// at 1s/s from the snapshot's wallclock, same as the tracking window.
const acquiringBarsShiftPx = ref(0)

function timeToLeft(seconds: number): number {
  return startWidthPx.value + seconds * pixelsPerSecond.value
}

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// Always draws the bar at the full max height so the max height reads as a fixed reference, with the
// score encoded as how much of that height is filled in with the opaque color vs. the faint background fill.
function drawConfidenceBar(ctx: CanvasRenderingContext2D, x: number, width: number, canvasHeight: number, score: number, color: string): void {
  const filledHeight = Math.max(0, Math.min(1, score)) * CONFIDENCE_BAR_MAX_HEIGHT
  const top = canvasHeight - CONFIDENCE_BAR_MAX_HEIGHT
  ctx.fillStyle = hexToRgba(color, CONFIDENCE_BAR_BG_ALPHA)
  ctx.fillRect(x, top, width, CONFIDENCE_BAR_MAX_HEIGHT - filledHeight)
  ctx.fillStyle = hexToRgba(color, CONFIDENCE_BAR_ALPHA)
  ctx.fillRect(x, canvasHeight - filledHeight, width, filledHeight)
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
    const x = Math.round(beat * pixelsPerSecond.value)
    ctx.fillRect(x, 0, 1, canvas.height)
  }
  ctx.globalAlpha = DOWNBEAT_ALPHA
  for (const beat of waveform.downbeats) {
    const x = Math.round(beat * pixelsPerSecond.value)
    ctx.fillRect(x, 0, 1, canvas.height)
  }
  ctx.globalAlpha = 1

  const half = WAVEFORM_LANE_HEIGHT / 2
  const vocalsCenter = half
  const novocalsCenter = WAVEFORM_LANE_HEIGHT + half
  const drawPeaks = (peaks: number[], center: number, color: string) => {
    ctx.fillStyle = color
    const step = barStepPx.value
    for (let i = 0; i < peaks.length; i++) {
      const h = Math.min(1, peaks[i]) * half
      const x = i * step
      ctx.fillRect(x, center - h, Math.max(1, step), Math.max(1, h * 2))
    }
  }
  ctx.globalAlpha = WAVEFORM_ALPHA
  drawPeaks(waveform.peaks.vocals, vocalsCenter, '#4a9eff')
  drawPeaks(waveform.peaks.novocals, novocalsCenter, '#7a7a7a')
  ctx.globalAlpha = 1
}

// Acquiring-phase confidence bars: no lock yet, so they span the whole scan range and sit at fixed absolute
// ref-time coordinates, same as the waveform - there's no "current position" for them to glide with.
function drawAcquiringConfidenceBars(): void {
  const canvas = acquiringBarsCanvas.value
  if (!canvas) return
  canvas.width = canvasWidthPx.value
  canvas.height = totalHeightPx.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  if (store.syncPhase !== 'acquiring' || !store.confidenceBars.length) return

  const candidateColorByBarIndex = new Map(store.bestCandidates.map((c, rank) => [c.barIndex, CANDIDATE_COLORS[rank]]))

  const height = canvas.height
  for (let i = 0; i < store.confidenceBars.length; i++) {
    const bar = store.confidenceBars[i]
    const x = bar.refSeconds * pixelsPerSecond.value
    const color = candidateColorByBarIndex.get(i) ?? ACQUIRING_BAR_COLOR
    drawConfidenceBar(ctx, x, Math.max(1, barStepPx.value), height, bar.score, color)
  }
}

// Tracking-phase confidence bars: a small window around the current position estimate. Drawn once into a
// snugly-sized canvas in local coordinates, then trackingBarsLeftPx (computed every tick, like positionLeftPx)
// carries it across the screen.
function drawTrackingConfidenceBars(): void {
  const canvas = trackingBarsCanvas.value
  if (!canvas) return
  const bars = store.confidenceBars
  if (store.syncPhase !== 'tracking' || !bars.length) {
    trackingBarsOriginSeconds.value = null
    return
  }
  trackingBarsOriginSeconds.value = bars[0].refSeconds
  canvas.width = trackingBarsWidthPx.value
  canvas.height = totalHeightPx.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const height = canvas.height
  for (let i = 0; i < bars.length; i++) {
    const x = i * barStepPx.value
    drawConfidenceBar(ctx, x, Math.max(1, barStepPx.value), height, bars[i].score, TRACKING_BAR_COLOR)
  }
}

function refreshLayout(): void {
  viewportWidthPx.value = containerEl.value?.clientWidth ?? 400
  viewportHeightPx.value = containerEl.value?.clientHeight ?? 200
  drawWaveform()
  drawAcquiringConfidenceBars()
  drawTrackingConfidenceBars()
}

function tick(): void {
  const nowMs = Date.now()
  const pps = pixelsPerSecond.value
  const frame = smoother.update(nowMs, store.positionAnchor, {
    autoScroll: autoScroll.value,
    scrollSeconds: (containerEl.value?.scrollLeft ?? 0) / pps,
    durationSeconds: durationSeconds.value,
  })
  displayPosition.value = frame.primaryPosition
  positionBars.value = frame.bars
  acquiringBarsShiftPx.value =
    store.snapshotWallclockMs === null ? 0 : ((Date.now() - store.snapshotWallclockMs) / 1000) * pixelsPerSecond.value
  if (frame.scrollPosition !== null && containerEl.value) {
    containerEl.value.scrollLeft = frame.scrollPosition * pps
  }
  rafId = requestAnimationFrame(tick)
}

function onTimelineDoubleClick(event: MouseEvent): void {
  if (!store.selectedSong) return
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const x = event.clientX - rect.left - startWidthPx.value
  const seconds = Math.max(0, x / pixelsPerSecond.value)
  const text = window.prompt('Timeline note text:')
  if (text) api.addTimelineNote(store.selectedSong.id, seconds, text)
}

function editNote(noteId: string, currentText: string): void {
  if (!store.selectedSong) return
  const text = window.prompt('Edit note (empty to delete):', currentText)
  if (text === null) return
  if (text === '') {
    api.deleteTimelineNote(store.selectedSong.id, noteId)
  } else {
    api.updateTimelineNote(store.selectedSong.id, noteId, { text })
  }
}

watch(() => store.waveform, () => nextTick(drawWaveform))
watch(() => store.selectedSong?.id, () => smoother.reset())
watch(pixelsPerSecond, () => nextTick(refreshLayout))
watch(
  () => [store.confidenceBars, store.bestCandidates, store.syncPhase],
  () =>
    nextTick(() => {
      drawAcquiringConfidenceBars()
      drawTrackingConfidenceBars()
    }),
)

let resizeObserver: ResizeObserver | undefined
let rafId = 0
onMounted(() => {
  refreshLayout()
  resizeObserver = new ResizeObserver(refreshLayout)
  if (containerEl.value) resizeObserver.observe(containerEl.value)
  rafId = requestAnimationFrame(tick)
})
onUnmounted(() => {
  resizeObserver?.disconnect()
  cancelAnimationFrame(rafId)
})
</script>

<template>
  <div class="timeline-wrap">
    <div class="timeline-toolbar">
      <label><input type="checkbox" v-model="autoScroll" /> auto-scroll</label>
    </div>
    <div class="timeline-outer">
      <div class="timeline-container" ref="containerEl">
        <div
          v-if="store.selectedSong"
          class="timeline"
          :style="{ width: `${timelineWidthPx}px` }"
          @dblclick="onTimelineDoubleClick"
        >
          <div class="start-area" :style="{ width: `${startWidthPx}px` }"></div>
          <canvas ref="waveCanvas" class="wave-canvas" :style="{ width: `${canvasWidthPx}px`, height: `${totalHeightPx}px` }" />
          <div class="end-area" :style="{ width: `${endWidthPx}px` }"></div>
          <canvas
            v-if="store.syncPhase === 'tracking'"
            ref="trackingBarsCanvas"
            class="confidence-overlay"
            :style="{ left: `${trackingBarsLeftPx ?? startWidthPx}px`, width: `${trackingBarsWidthPx}px`, height: `${totalHeightPx}px` }"
          />
          <canvas
            v-else
            ref="acquiringBarsCanvas"
            class="confidence-overlay"
            :style="{ left: `${startWidthPx + acquiringBarsShiftPx}px`, width: `${canvasWidthPx}px`, height: `${totalHeightPx}px` }"
          />
          <div
            v-for="note in store.selectedSong.timelineNotes"
            :key="note.id"
            class="timeline-note"
            :style="{ left: `${timeToLeft(note.timeSeconds)}px` }"
            @click="editNote(note.id, note.text)"
          >
            {{ note.text }}
          </div>
          <div
            v-for="(bar, i) in positionBars"
            :key="i"
            class="position-bar"
            :style="{ left: `${positionToLeft(bar.position)}px`, opacity: bar.opacity }"
          />
        </div>
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
}
.timeline-outer {
  position: relative;
  flex: 1;
  overflow: hidden;
}
.timeline-container {
  width: 100%;
  height: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  position: relative;
}
.timeline {
  position: relative;
  display: flex;
  height: 100%;
  background: #050506;
}
.start-area,
.end-area {
  flex: none;
  height: 100%;
  background: repeating-linear-gradient(45deg, #050506 0 8px, #101114 8px 16px);
}
.wave-canvas {
  flex: none;
  display: block;
}
.confidence-overlay {
  position: absolute;
  top: 0;
  pointer-events: none;
  z-index: 2;
}
.position-bar {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: #fff;
  z-index: 3;
}
.timeline-note {
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
