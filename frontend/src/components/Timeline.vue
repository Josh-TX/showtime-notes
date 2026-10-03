<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useShowStore } from '../store/show'
import { clientSettings } from '../store/clientSettings'
import { playerPause, playerPlay, playerSeek, playerSetSpeed, playerSetStem, playerStop, songPlayer, type PlayerSpeed, type Stem } from '../audio/songPlayer'
import RadioButtonGroup from './RadioButtonGroup.vue'
import TimelineNotes from './TimelineNotes.vue'
import { PositionSmoother, type BarState } from './smoothing'
import ScaleBar from './ScaleBar.vue'
import { isZoomWheel, useTimelineZoom } from './useTimelineZoom'
import { PEAKS_PER_SECOND, computeTiles, drawWaveformTile, prepareTile } from './timelineDraw'

const CONFIDENCE_BAR_ALPHA = 0.7
const CONFIDENCE_BAR_BG_ALPHA = 0.03
const CONFIDENCE_BAR_MAX_HEIGHT = 120
const ACQUIRING_BAR_COLOR = '#e0c33e'
const TRACKING_BAR_COLOR = '#3ecf5f'
// Rank order (best candidate first) maps to these colors; shared with CandidatesPanel.vue's color key.
const CANDIDATE_COLORS = ['#00e5ff', '#ff00ff', '#ff9800']

const store = useShowStore()

const containerEl = ref<HTMLDivElement | null>(null)
const waveTileCanvases: (HTMLCanvasElement | null)[] = []
const acquiringTileCanvases: (HTMLCanvasElement | null)[] = []
const trackingBarsCanvas = ref<HTMLCanvasElement | null>(null)

const viewportWidthPx = ref(400)
const viewportHeightPx = ref(200)
const scrollbarHeightPx = ref(0)
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
const tiles = computed(() => computeTiles(canvasWidthPx.value))

function positionToLeft(position: number): number {
  return startWidthPx.value + position * pixelsPerSecond.value
}

// Confidence bars are one per chroma frame (backend chroma.py HOP/SR), not per waveform peak
const CHROMA_FRAME_SECONDS = 1102 / 22050
const barStepPx = computed(() => pixelsPerSecond.value * CHROMA_FRAME_SECONDS)
const trackingBarsWidthPx = computed(() => Math.max(1, store.confidenceBars.length * barStepPx.value))
// Mirrors positionLeftPx's anchor extrapolation, offset by where the drawn window's first bar sits relative to
// the anchor - so the window glides in lockstep with the position bar instead of jumping on every new snapshot.
const trackingBarsLeftPx = computed(() => {
  const anchor = store.positionAnchor
  if (anchor === null || trackingBarsOriginSeconds.value === null || displayPosition.value === null) return null
  const drift = displayPosition.value - anchor.refSeconds
  // refSeconds is the frame center, so the first bar's left edge is half a step earlier
  return startWidthPx.value + (trackingBarsOriginSeconds.value + drift) * pixelsPerSecond.value - barStepPx.value / 2
})

// Acquiring bars are anchors too ("live-now is at this ref time"), so between snapshots they glide right
// at 1s/s from the snapshot's wallclock, same as the tracking window.
const acquiringBarsShiftPx = ref(0)

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
  const waveform = store.waveform
  if (!waveform) return
  for (const tile of tiles.value) {
    const ctx = prepareTile(waveTileCanvases[tile.index], tile, totalHeightPx.value)
    if (ctx) drawWaveformTile(ctx, tile, totalHeightPx.value, pixelsPerSecond.value, waveform)
  }
}

// Acquiring-phase confidence bars: no lock yet, so they span the whole scan range and sit at fixed absolute
// ref-time coordinates, same as the waveform - there's no "current position" for them to glide with.
function drawAcquiringConfidenceBars(): void {
  const active = store.syncPhase === 'acquiring' && store.confidenceBars.length > 0
  const candidateColorByBarIndex = new Map(store.bestCandidates.map((c, rank) => [c.barIndex, CANDIDATE_COLORS[rank]]))
  const height = totalHeightPx.value
  const barWidth = Math.max(1, barStepPx.value)
  for (const tile of tiles.value) {
    const ctx = prepareTile(acquiringTileCanvases[tile.index], tile, totalHeightPx.value)
    if (!ctx || !active) continue
    const right = tile.left + tile.width
    for (let i = 0; i < store.confidenceBars.length; i++) {
      const bar = store.confidenceBars[i]
      const x = bar.refSeconds * pixelsPerSecond.value - barWidth / 2
      if (x + barWidth < tile.left || x >= right) continue
      const color = candidateColorByBarIndex.get(i) ?? ACQUIRING_BAR_COLOR
      drawConfidenceBar(ctx, x, barWidth, height, bar.score, color)
    }
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
  // 0 for overlay scrollbars; measured so the scale bar clears whatever the platform draws
  scrollbarHeightPx.value = containerEl.value ? containerEl.value.offsetHeight - containerEl.value.clientHeight : 0
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
  } else if (playbackVisible.value && autoScroll.value && containerEl.value) {
    const targetPx = songPlayer.position * pps
    let px = targetPx
    if (seekScroll) {
      const t = (nowMs - seekScroll.startMs) / SEEK_SCROLL_MS
      if (t >= 1) seekScroll = null
      else px = seekScroll.startPx + (targetPx - seekScroll.startPx) * (1 - (1 - t) ** 3)
    }
    containerEl.value.scrollLeft = px
  }
  rafId = requestAnimationFrame(tick)
}

// Direct user scroll input (wheel, touch, scrollbar drag) turns auto-scroll off; programmatic scrollLeft doesn't.
function onUserScroll(event?: Event): void {
  if (event instanceof WheelEvent && isZoomWheel(event)) return
  autoScroll.value = false
}
function onContainerPointerDown(event: PointerEvent): void {
  // pointerdown targets the container itself only on its scrollbar; timeline content is a child
  if (event.target === containerEl.value) autoScroll.value = false
}
// Zoom pivots on the position bar when auto-scroll is driving the scroll; otherwise on the cursor/pinch center
useTimelineZoom({
  containerEl,
  startWidthPx: () => startWidthPx.value,
  pixelsPerSecond: () => pixelsPerSecond.value,
  scrollIsDriven: () => autoScroll.value && (store.syncPhase === 'tracking' || playbackVisible.value),
})
const SEEKBAR_HEIGHT = 24
const SEEK_SCROLL_MS = 200
// Set on each seek so auto-scroll eases from the current scroll to the (live) playback position
let seekScroll: { startPx: number; startMs: number } | null = null
const SEEKBAR_BOTTOM = 20
const STEMS: Stem[] = ['original', 'vocals', 'novocals']
const SPEEDS = ['1x', '2x', '3x', '4x'] as const
const stem = computed(() => songPlayer.stem)
const speedLabel = computed(() => `${songPlayer.speed}x` as (typeof SPEEDS)[number])

// Playback is only available on ready songs (so never while syncing)
const playbackAllowed = computed(() => store.selectedSong?.status === 'ready')
const playbackVisible = playbackAllowed
const seekFraction = computed(() => (durationSeconds.value > 0 ? Math.min(1, songPlayer.position / durationSeconds.value) : 0))

function togglePlay(): void {
  const id = store.selectedSong?.id
  if (!id) return
  if (songPlayer.playing) playerPause()
  else playerPlay(id)
}

function seekForward(): void {
  const id = store.selectedSong?.id
  if (!id) return
  const max = durationSeconds.value > 0 ? durationSeconds.value : Infinity
  playerSeek(id, Math.min(max, songPlayer.position + 5), 100)
}

function seekBackward(): void {
  const id = store.selectedSong?.id
  if (!id) return
  playerSeek(id, Math.max(0, songPlayer.position - 5), 100)
}

function isSpaceToggle(event: KeyboardEvent): boolean {
  if (event.code !== 'Space' || event.ctrlKey || event.metaKey || event.altKey) return false
  const el = event.target as HTMLElement | null
  if (el?.closest('input:not([type=checkbox]):not([type=radio]), textarea, select, [contenteditable]')) return false
  return playbackVisible.value
}

function onKeyDown(event: KeyboardEvent): void {
  if (!isSpaceToggle(event)) return
  event.preventDefault() // also stops page scroll / focused-button activation
  if (!event.repeat) togglePlay()
}

// Space on a focused button fires click on keyup; swallow it so it doesn't double-toggle
function onKeyUp(event: KeyboardEvent): void {
  if (isSpaceToggle(event)) event.preventDefault()
}

function seekFromEvent(event: PointerEvent): void {
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const seconds = ((event.clientX - rect.left) / rect.width) * durationSeconds.value
  const id = store.selectedSong?.id
  if (id && containerEl.value) seekScroll = { startPx: containerEl.value.scrollLeft, startMs: Date.now() }
  if (id) playerSeek(id, Math.min(durationSeconds.value, Math.max(0, seconds)))
}

function onSeekDown(event: PointerEvent): void {
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  seekFromEvent(event)
}

function onSeekMove(event: PointerEvent): void {
  if ((event.currentTarget as HTMLElement).hasPointerCapture(event.pointerId)) seekFromEvent(event)
}

watch(() => store.waveform, () => nextTick(drawWaveform))
watch(() => store.selectedSong?.id, () => {
  smoother.reset()
  playerStop()
})
watch(playbackAllowed, (ok) => {
  if (!ok) playerStop()
})
// Re-enabling auto-scroll eases from the current scroll to the playback position instead of snapping
watch(autoScroll, (on) => {
  if (on && containerEl.value) seekScroll = { startPx: containerEl.value.scrollLeft, startMs: Date.now() }
})
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
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', onKeyUp)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', onKeyUp)
  resizeObserver?.disconnect()
  cancelAnimationFrame(rafId)
})
</script>

<template>
  <div class="timeline-wrap">
    <div class="timeline-toolbar">
      <label class="auto-scroll">
        <input type="checkbox" v-model="autoScroll" />
        auto-scroll
      </label>
      <div v-if="playbackVisible" class="playback-controls">
        <button
          type="button"
          class="seek-btn"
          aria-label="seek backward 5 seconds"
          @click="seekBackward"
        >
          <svg viewBox="0 0 24 24" class="seek-icon" aria-hidden="true">
            <g transform="translate(24 0) scale(-1 1) rotate(45 12 13)">
              <path d="M20 13A8 8 0 1 1 12 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
              <path d="M15 5L12 8V2z" fill="currentColor" />
            </g>
            <text x="10" y="16" text-anchor="middle" font-size="9" font-weight="700" fill="currentColor">−5</text>
          </svg>
        </button>
        <button
          type="button"
          class="play-btn"
          :aria-label="songPlayer.playing ? 'pause' : 'play'"
          @click="togglePlay"
        >
          <svg viewBox="0 0 24 24" class="play-icon" aria-hidden="true">
            <path v-if="songPlayer.playing" d="M6 5h4v14H6zM14 5h4v14h-4z" fill="currentColor" />
            <path v-else d="M8 5v14l11-7z" fill="currentColor" />
          </svg>
        </button>
        <button
          type="button"
          class="seek-btn"
          aria-label="seek forward 5 seconds"
          @click="seekForward"
        >
          <svg viewBox="0 0 24 24" class="seek-icon" aria-hidden="true">
            <g transform="rotate(45 12 13)">
              <path d="M20 13A8 8 0 1 1 12 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
              <path d="M15 5L12 8V2z" fill="currentColor" />
            </g>
            <text x="11" y="16" text-anchor="middle" font-size="9" font-weight="700" fill="currentColor">+5</text>
          </svg>
        </button>
        <RadioButtonGroup
          :model-value="stem"
          :options="STEMS"
          font-size="1.1rem"
          accent="rgb(133, 74, 209)"
          @update:model-value="playerSetStem"
        />
        <RadioButtonGroup
          :model-value="speedLabel"
          :options="SPEEDS"
          font-size="1.1rem"
          accent="rgb(133, 74, 209)"
          @update:model-value="(v) => playerSetSpeed(parseInt(v) as PlayerSpeed)"
        />
      </div>
    </div>
    <div class="timeline-outer">
      <div
        class="timeline-container"
        ref="containerEl"
        @wheel.passive="onUserScroll"
        @touchmove.passive="onUserScroll"
        @pointerdown="onContainerPointerDown"
      >
        <div
          v-if="store.selectedSong"
          class="timeline"
          :style="{ width: `${timelineWidthPx}px` }"
        >
          <div class="start-area" :style="{ width: `${startWidthPx}px` }"></div>
          <div class="wave-tiles" :style="{ width: `${canvasWidthPx}px`, height: `${totalHeightPx}px` }">
            <canvas
              v-for="tile in tiles"
              :key="tile.index"
              :ref="(el) => (waveTileCanvases[tile.index] = el as HTMLCanvasElement | null)"
              class="tile-canvas"
              :style="{ left: `${tile.left}px`, width: `${tile.width}px`, height: `${totalHeightPx}px` }"
            />
          </div>
          <div class="end-area" :style="{ width: `${endWidthPx}px` }"></div>
          <div
            v-if="playbackVisible"
            class="seekbar"
            :style="{
              left: `${startWidthPx}px`,
              width: `${canvasWidthPx}px`,
              height: `${SEEKBAR_HEIGHT}px`,
              bottom: `${SEEKBAR_BOTTOM}px`,
            }"
            @pointerdown.stop="onSeekDown"
            @pointermove="onSeekMove"
            @click.stop
          >
            <div class="seekbar-fill" :style="{ width: `${seekFraction * 100}%` }"></div>
          </div>
          <canvas
            v-if="store.syncPhase === 'tracking'"
            ref="trackingBarsCanvas"
            class="confidence-overlay"
            :style="{ left: `${trackingBarsLeftPx ?? startWidthPx}px`, width: `${trackingBarsWidthPx}px`, height: `${totalHeightPx}px` }"
          />
          <div
            v-else
            class="confidence-overlay"
            :style="{ left: `${startWidthPx + acquiringBarsShiftPx}px`, width: `${canvasWidthPx}px`, height: `${totalHeightPx}px` }"
          >
            <canvas
              v-for="tile in tiles"
              :key="tile.index"
              :ref="(el) => (acquiringTileCanvases[tile.index] = el as HTMLCanvasElement | null)"
              class="tile-canvas"
              :style="{ left: `${tile.left}px`, width: `${tile.width}px`, height: `${totalHeightPx}px` }"
            />
          </div>
          <TimelineNotes :start-width-px="startWidthPx" :pixels-per-second="pixelsPerSecond" :beats="store.waveform?.beats" :downbeats="store.waveform?.downbeats" />
          <div
            v-if="playbackVisible"
            class="playback-bar"
            :style="{ left: `${positionToLeft(songPlayer.position)}px` }"
          />
          <div
            v-for="(bar, i) in positionBars"
            :key="i"
            class="position-bar"
            :style="{ left: `${positionToLeft(bar.position)}px`, opacity: bar.opacity }"
          />
        </div>
      </div>
      <ScaleBar :pixels-per-second="pixelsPerSecond" :bottom-offset-px="scrollbarHeightPx" />
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
  flex: none;
  box-sizing: border-box;
  height: 34px;
  padding: 0 0.6rem;
  font-size: 0.8rem;
  border-bottom: 1px solid #2a2a2a;
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.timeline-outer {
  position: relative;
  flex: 1;
  overflow: hidden;
}
.timeline-container {
  width: 100%;
  height: 100%;
  overflow-x: scroll;
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
.wave-tiles {
  flex: none;
  position: relative;
}
.tile-canvas {
  position: absolute;
  top: 0;
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
  background: #3ecf5f;
  z-index: 6;
}
</style>
<style scoped>
.seekbar {
  position: absolute;
  background: rgba(133, 74, 209, 0.22);
  z-index: 4;
  cursor: pointer;
  touch-action: none;
}
.seekbar-fill {
  height: 100%;
  background: rgb(133, 74, 209);
  pointer-events: none;
}
.playback-bar {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: rgb(133, 74, 209);
  z-index: 6;
  pointer-events: none;
}
.playback-controls {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 1rem;
}
.play-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0;
  color: #fff;
  background: rgb(133, 74, 209);
  border: 0;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.15s, box-shadow 0.15s;
}
.play-btn:hover {
  background: rgb(153, 94, 229);
}
.play-btn:active {
  transform: scale(0.95);
}
.seek-btn {
  display: flex;
  padding: 0;
  color: rgb(133, 74, 209);
  background: transparent;
  border: 0;
  cursor: pointer;
}
.seek-btn:hover {
  color: rgb(153, 94, 229);
}
.seek-btn:active {
  transform: scale(0.92);
}
.seek-icon {
  width: 2.2rem;
  height: 2.2rem;
}
.play-icon {
  width: 1.2rem;
  height: 1.2rem;
}
.play-btn {
  width: 3.6rem;
  height: 1.8rem;
  border-radius: 999px;
}
.auto-scroll {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.2rem;
  cursor: pointer;
  user-select: none;
}
.auto-scroll input {
  width: 1.3rem;
  height: 1.3rem;
  margin: 0;
  cursor: pointer;
}
</style>
