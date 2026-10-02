<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'
import { NOTE_COLORS } from '../store/noteColors'
import type { TimelineNote } from '../types'

// Notes + selected-position marker, overlaid on a timeline whose t=0 sits at startWidthPx.
// beats (seconds) enable snapping while dragging; omit for timelines without beats.
const props = defineProps<{ startWidthPx: number; pixelsPerSecond: number; beats?: number[]; downbeats?: number[] }>()

const store = useShowStore()

const NOTE_HEIGHT = 32
// A dragged note's left edge snaps to a beat when within this many pixels of it.
const BEAT_SNAP_RANGE_PX = 10
// A press on the drag handle becomes a drag after moving this far, or after being held this long. The hold
// matters during auto-scroll, where the timeline moves under a mouse that never does.
const DRAG_START_DISTANCE_PX = 4
const DRAG_HOLD_MS = 200

const layer = ref<HTMLElement | null>(null)
const dragId = ref<string | null>(null)
// Live position of the dragged note (last valid spot); only saved on release.
const draft = ref<{ id: string; timeSeconds: number; y: number } | null>(null)
const dragValid = ref(true)
const snapLineSeconds = ref<number | null>(null)

// Press state. A press is "pending" until it turns into a drag (dragId set) or is released.
let pressId: string | null = null
let pressTimeMs = 0
let pressX = 0
let pressY = 0
let pointerX = 0
let pointerY = 0
let grabX = 0
let grabY = 0
let frameHandle = 0
let justDragged = false

function snapToBeat(seconds: number): { seconds: number; snapped: boolean } {
  let best = seconds
  let snapped = false
  let bestDistPx = BEAT_SNAP_RANGE_PX
  for (const beat of props.beats ?? []) {
    const distPx = Math.abs(beat - seconds) * props.pixelsPerSecond
    if (distPx <= bestDistPx) {
      best = beat
      snapped = true
      bestDistPx = distPx
    }
  }
  return { seconds: best, snapped }
}

// Where the dragged note would land for the current pointer position, or null if that spot is invalid.
function dropTarget(): { timeSeconds: number; y: number; snapped: boolean } | null {
  const rect = layer.value?.getBoundingClientRect()
  if (!rect) return null
  const snap = snapToBeat((pointerX - rect.left - grabX - props.startWidthPx) / props.pixelsPerSecond)
  const y = pointerY - rect.top - grabY
  if (snap.seconds < 0 || snap.seconds > store.maxNoteSeconds) return null
  if (y < 0 || y > rect.height - NOTE_HEIGHT) return null
  return { timeSeconds: snap.seconds, y, snapped: snap.snapped }
}

// Runs every frame while a press is active: the timeline can scroll under a stationary pointer, so the target
// is recomputed from the last pointer position and the current scroll offset, not only on pointer events.
function frame(): void {
  if (pressId === null) return
  if (dragId.value === null && performance.now() - pressTimeMs >= DRAG_HOLD_MS) startDrag()
  if (dragId.value !== null) {
    const target = dropTarget()
    dragValid.value = target !== null
    if (target) draft.value = { id: dragId.value, timeSeconds: target.timeSeconds, y: target.y }
    snapLineSeconds.value = target?.snapped ? target.timeSeconds : null
  }
  frameHandle = requestAnimationFrame(frame)
}

function startDrag(): void {
  dragId.value = pressId
}

function onPointerDown(e: PointerEvent, note: TimelineNote): void {
  if (e.button !== 0) return
  const noteEl = (e.currentTarget as HTMLElement).parentElement!
  const r = noteEl.getBoundingClientRect()
  grabX = e.clientX - r.left
  grabY = e.clientY - r.top
  pressId = note.id
  pressTimeMs = performance.now()
  pressX = pointerX = e.clientX
  pressY = pointerY = e.clientY
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  window.addEventListener('keydown', onKeyDown)
  frameHandle = requestAnimationFrame(frame)
}

function onPointerMove(e: PointerEvent): void {
  if (pressId === null) return
  pointerX = e.clientX
  pointerY = e.clientY
  if (dragId.value === null && Math.hypot(pointerX - pressX, pointerY - pressY) >= DRAG_START_DISTANCE_PX) startDrag()
}

function onPointerUp(): void {
  const id = dragId.value
  const target = id ? dropTarget() : null
  const song = store.selectedSong
  const note = song?.timelineNotes.find((n) => n.id === id)
  if (target && song && note) {
    note.timeSeconds = target.timeSeconds
    note.y = target.y
    api.updateTimelineNote(song.id, note.id, { timeSeconds: target.timeSeconds, y: target.y })
  }
  endDrag()
}

function onKeyDown(e: KeyboardEvent): void {
  if (e.key === 'Escape') endDrag()
}

function endDrag(): void {
  if (dragId.value !== null) {
    // the click that follows a drag's pointerup must not select/deselect the note
    justDragged = true
    setTimeout(() => (justDragged = false))
  }
  pressId = dragId.value = draft.value = snapLineSeconds.value = null
  dragValid.value = true
  cancelAnimationFrame(frameHandle)
  window.removeEventListener('keydown', onKeyDown)
}

onBeforeUnmount(endDrag)

function onNoteClick(id: string): void {
  if (justDragged) return
  if (store.selectedNoteId === id) store.deselect()
  else store.selectNote(id)
}

function noteTimeSeconds(note: TimelineNote): number {
  return draft.value?.id === note.id ? draft.value.timeSeconds : note.timeSeconds
}

function noteY(note: TimelineNote): number {
  return draft.value?.id === note.id ? draft.value.y : note.y
}

function left(seconds: number): number {
  return props.startWidthPx + seconds * props.pixelsPerSecond
}
</script>

<template>
  <div ref="layer" class="notes-layer">
    <div
      v-for="note in store.selectedSong?.timelineNotes ?? []"
      :key="note.id"
      class="timeline-note"
      :class="{
        selected: note.id === store.selectedNoteId,
        dragging: note.id === dragId,
        invalid: note.id === dragId && !dragValid,
      }"
      :style="{
        left: `${left(noteTimeSeconds(note))}px`,
        top: `${noteY(note)}px`,
        borderColor: NOTE_COLORS[note.color],
        '--note-color': NOTE_COLORS[note.color],
      }"
      @click.stop="onNoteClick(note.id)"
    >
      <span class="text">{{ note.text }}</span>
      <span
        class="drag-handle"
        title="Drag to move"
        @pointerdown="onPointerDown($event, note)"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="endDrag"
        @click.stop
        >⠿</span
      >
    </div>
    <div
      v-if="snapLineSeconds !== null"
      class="snap-line"
      :class="{ downbeat: props.downbeats?.includes(snapLineSeconds) }"
      :style="{ left: `${left(snapLineSeconds)}px` }" />
    <div
      v-if="store.selectedPosition"
      class="position-marker"
      :style="{ left: `${left(store.selectedPosition.timeSeconds)}px`, top: `${store.selectedPosition.y}px` }"
    />
  </div>
</template>

<style scoped>
.notes-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 4;
}
.timeline-note {
  position: absolute;
  height: 32px;
  line-height: 30px;
  padding: 0 30px 0 8px;
  max-width: 800px;
  display: flex;
  align-items: center;
  white-space: nowrap;
  font-size: 1.6rem;
  text-transform: uppercase;
  color: #fff;
  background: rgba(10, 10, 12, 0.75);
  border: 1px solid;
  border-left-width: 4px;
  box-shadow: 0 0 8px 1px #000;
  pointer-events: auto;
  cursor: pointer;
  user-select: none;
}
.text {
  overflow: hidden;
  text-overflow: ellipsis;
}
.drag-handle {
  cursor: grab;
  color: var(--note-color);
  opacity: 0.8;
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 34px;
  padding: 4px 0 0 2px; /* nudges the dots 2px below and 1px right of center */
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  line-height: 1;
  touch-action: none;
}
.timeline-note.dragging .drag-handle {
  cursor: grabbing;
}
.timeline-note.invalid {
  opacity: 0.4;
}
.timeline-note.invalid .drag-handle {
  cursor: not-allowed;
}
.drag-handle:hover {
  opacity: 1;
}
.timeline-note.dragging,
.timeline-note.selected {
  box-shadow: 0 0 0 1px #00e5ff, 0 0 8px #00e5ff;
  z-index: 1;
}
.snap-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  margin-left: -1px;
  background: #6b4709;
  opacity: 0.8;
  box-shadow: 0 0 6px #6b4709;
}
.snap-line.downbeat {
  background: #d9971a;
  box-shadow: 0 0 6px #d9971a;
}
.position-marker {
  position: absolute;
  width: 1px;
  height: 32px;
  background: #00e5ff;
  box-shadow: 0 0 6px 1px #00e5ff;
}
</style>
