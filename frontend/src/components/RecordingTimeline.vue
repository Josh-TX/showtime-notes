<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useShowStore } from '../store/show'
import { clientSettings } from '../store/clientSettings'
import TimelineNotes from './TimelineNotes.vue'
import ScaleBar from './ScaleBar.vue'
import { isZoomWheel, useTimelineZoom } from './useTimelineZoom'
import { computeTiles, drawLoudnessTile, prepareTile, stretchLoudness } from './timelineDraw'

const LIVE_PEAKS_PER_SECOND = 50

const store = useShowStore()

const containerEl = ref<HTMLDivElement | null>(null)
const displayPeaks: number[] = [] // store.recordingPeaks after contrast stretching
const tileCanvases: (HTMLCanvasElement | null)[] = []

const viewportWidthPx = ref(400)
const viewportHeightPx = ref(200)
const scrollbarHeightPx = ref(0)
const followLive = ref(true)

const pixelsPerSecond = computed(() => viewportWidthPx.value / clientSettings.timelineWidthSeconds)
const elapsedSeconds = computed(() => store.recordingPeaks.length / LIVE_PEAKS_PER_SECOND)
// The live edge sits at the right edge of the container (100% offset), so the left padding is a full viewport.
const startWidthPx = computed(() => viewportWidthPx.value)
const canvasWidthPx = computed(() => Math.max(1, elapsedSeconds.value * pixelsPerSecond.value))
const timelineWidthPx = computed(() => startWidthPx.value + canvasWidthPx.value)
const tiles = computed(() => computeTiles(canvasWidthPx.value))

function formatElapsed(seconds: number): string {
  const total = Math.floor(seconds)
  const mm = Math.floor(total / 60)
  const ss = total % 60
  return `${mm}:${ss.toString().padStart(2, '0')}`
}

// Redraws every tile that reaches past `fromSeconds`; tiles entirely before it can't have changed.
function draw(fromSeconds = 0): void {
  const fromPx = fromSeconds * pixelsPerSecond.value
  const height = viewportHeightPx.value
  stretchLoudness(store.recordingPeaks, displayPeaks, LIVE_PEAKS_PER_SECOND)
  for (const tile of tiles.value) {
    if (tile.left + tile.width < fromPx) continue
    const ctx = prepareTile(tileCanvases[tile.index], tile, height)
    if (!ctx) continue
    drawLoudnessTile(ctx, tile, pixelsPerSecond.value, displayPeaks, LIVE_PEAKS_PER_SECOND)
  }
}

function scrollToLive(): void {
  if (followLive.value && containerEl.value) containerEl.value.scrollLeft = containerEl.value.scrollWidth
}

function refreshLayout(): void {
  viewportWidthPx.value = containerEl.value?.clientWidth ?? 400
  viewportHeightPx.value = containerEl.value?.clientHeight ?? 200
  // 0 for overlay scrollbars; measured so the scale bar clears whatever the platform draws
  scrollbarHeightPx.value = containerEl.value ? containerEl.value.offsetHeight - containerEl.value.clientHeight : 0
  nextTick(() => {
    draw()
    scrollToLive()
  })
}

// The trace only grows at the live edge (a little overlap for the last bar's width).
watch(elapsedSeconds, (seconds, prev) => {
  nextTick(() => {
    draw(Math.min(seconds, prev) - 1)
    scrollToLive()
  })
})
watch(followLive, scrollToLive)

// Programmatic scrolls don't fire these, so any of them means the user took over. Pointer-down only counts on
// the container itself (its scrollbar), so clicking the timeline keeps following.
function stopFollowing(event?: WheelEvent): void {
  if (event && isZoomWheel(event)) return
  followLive.value = false
}

// Zoom pivots on the live edge while following; otherwise on the cursor/pinch center
useTimelineZoom({
  containerEl,
  startWidthPx: () => startWidthPx.value,
  pixelsPerSecond: () => pixelsPerSecond.value,
  scrollIsDriven: () => followLive.value,
})
watch(pixelsPerSecond, () =>
  nextTick(() => {
    draw()
    scrollToLive()
  }),
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
  <div class="timeline-wrap">
    <div class="timeline-toolbar">
      <label><input type="checkbox" v-model="followLive" /> follow live</label>
      <span class="elapsed">{{ formatElapsed(elapsedSeconds) }}</span>
    </div>
    <div class="timeline-outer">
    <div
      class="timeline-container"
      ref="containerEl"
      @wheel.passive="stopFollowing"
      @touchmove.passive="stopFollowing"
      @pointerdown.self="stopFollowing"
    >
      <div class="timeline" :style="{ width: `${timelineWidthPx}px` }">
        <div class="start-area" :style="{ width: `${startWidthPx}px` }"></div>
        <div class="wave-tiles" :style="{ left: `${startWidthPx}px`, width: `${canvasWidthPx}px` }">
          <canvas
            v-for="tile in tiles"
            :key="tile.index"
            :ref="(el) => (tileCanvases[tile.index] = el as HTMLCanvasElement | null)"
            class="tile-canvas"
            :style="{ left: `${tile.left}px`, width: `${tile.width}px`, height: `${viewportHeightPx}px` }"
          />
        </div>
        <TimelineNotes :start-width-px="startWidthPx" :pixels-per-second="pixelsPerSecond" />
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
.timeline-outer {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.timeline-container {
  flex: 1;
  overflow-x: scroll;
  overflow-y: hidden;
  position: relative;
}
.timeline {
  position: relative;
  height: 100%;
  background: #050506;
}
.start-area {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: repeating-linear-gradient(45deg, #050506 0 8px, #101114 8px 16px);
}
.wave-tiles {
  position: absolute;
  top: 0;
  height: 100%;
}
.tile-canvas {
  position: absolute;
  top: 0;
  display: block;
}
</style>
