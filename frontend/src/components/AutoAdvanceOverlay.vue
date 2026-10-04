<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useShowStore } from '../store/show'
import { clientSettings } from '../store/clientSettings'

// Half the total transition: cover-up, then reveal. The song switch happens at the midpoint.
const AUTO_SELECT_TRANSITION_MS = 250

const store = useShowStore()
const runId = ref(0)
const sweepStyle = ref<Record<string, string>>({})
const visible = ref(false)
let firedForSongId: string | null = null
let timers: number[] = []
let rafId = 0

// Diagonal wipe: a soft-edged opaque band sweeps from the bottom-right to the top-left corner. Along the gradient
// line (top-left -> bottom-right, length L for the screen) the profile is: L clear, RAMP up, plateau, RAMP down,
// L clear. Sliding the screen-sized window across it peaks at the animation midpoint.
const SWEEP_RAMP_PX = 1000
// Opaque plateau length as a fraction of the screen's gradient length; smaller = corners stay slightly see-through
// at the midpoint.
const SWEEP_PLATEAU_FRACTION = 0.4
const SWEEP_COLOR = '0, 0, 0'

function prepareSweep(): void {
  const L = (window.innerWidth + window.innerHeight) / Math.SQRT2
  const ramp = SWEEP_RAMP_PX
  const plateau = L * SWEEP_PLATEAU_FRACTION
  const total = 2 * L + 2 * ramp + plateau
  const side = total / Math.SQRT2
  const shift = (L + 2 * ramp + plateau) / Math.SQRT2
  const clear = `rgba(${SWEEP_COLOR}, 0)`
  const solid = `rgb(${SWEEP_COLOR})`
  sweepStyle.value = {
    backgroundImage: `linear-gradient(135deg, ${clear} ${L}px, ${solid} ${L + ramp}px, ${solid} ${L + ramp + plateau}px, ${clear} ${L + 2 * ramp + plateau}px)`,
    backgroundSize: `${side}px ${side}px`,
    '--shift': `${-shift}px`,
    animationDuration: `${AUTO_SELECT_TRANSITION_MS * 2}ms`,
  }
}

function nextSongId(id: string): string | null {
  const songs = store.show?.songs ?? []
  const idx = songs.findIndex((s) => s.id === id)
  return idx >= 0 && idx + 1 < songs.length ? songs[idx + 1].id : null
}

function transitionTo(id: string): void {
  if (visible.value) return
  prepareSweep()
  runId.value++
  visible.value = true
  timers.push(
    window.setTimeout(() => store.selectSong(id), AUTO_SELECT_TRANSITION_MS),
    window.setTimeout(() => (visible.value = false), AUTO_SELECT_TRANSITION_MS * 2),
  )
}

function tick(): void {
  rafId = requestAnimationFrame(tick)
  const anchor = store.positionAnchor
  const song = store.selectedSong
  // selectSong sets selectedSongId/anchor immediately but selectedSong lags behind the fetch; skip the mismatch
  // window or the new song's anchor gets compared against the old song's duration.
  if (!anchor || !song?.durationSeconds || song.id !== store.selectedSongId || firedForSongId === song.id) return
  const position = anchor.refSeconds + (Date.now() - anchor.wallclockMs) / 1000
  const remaining = song.durationSeconds - position
  if (remaining > clientSettings.autoSelectNextSeconds + AUTO_SELECT_TRANSITION_MS / 1000) return
  const next = nextSongId(song.id)
  if (!next) return
  firedForSongId = song.id
  transitionTo(next)
}

// The server moved on from the song this client was viewing (e.g. the setting is tiny): follow it.
watch(
  () => store.show?.sync.targetSongId ?? null,
  (target, prev) => {
    if (target && prev && prev === store.selectedSongId && target !== store.selectedSongId) transitionTo(target)
  },
)

onMounted(() => (rafId = requestAnimationFrame(tick)))
onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
  timers.forEach(clearTimeout)
})
</script>

<template>
  <div
    v-if="visible"
    :key="runId"
    class="overlay"
    :style="sweepStyle"
  />
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background-repeat: no-repeat;
  pointer-events: none;
  animation-name: sweep;
  animation-timing-function: linear;
  animation-fill-mode: both;
}
@keyframes sweep {
  from {
    background-position: 0 0;
  }
  to {
    background-position: var(--shift) var(--shift);
  }
}
</style>
