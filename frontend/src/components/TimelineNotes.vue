<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'
import { beginNoteDrag, noteDrag, addNoteDropHandler } from '../store/noteDrag'
import NoteChip from './NoteChip.vue'
import NoteContextMenu from './NoteContextMenu.vue'
import type { TimelineNote } from '../types'

// Notes overlaid on a timeline whose t=0 sits at startWidthPx; also the drop target for note drags.
// beats (seconds) enable snapping while dragging; omit for timelines without beats.
const props = defineProps<{ startWidthPx: number; pixelsPerSecond: number; beats?: number[]; downbeats?: number[] }>()

const store = useShowStore()

const NOTE_HEIGHT = 32
// A dragged note's left edge snaps to a beat when within this many pixels of it.
const BEAT_SNAP_RANGE_PX = 10

const layer = ref<HTMLElement | null>(null)
// Where the dragged note would land; null when the pointer isn't over a valid spot. Only saved on release.
const draft = ref<{ timeSeconds: number; y: number } | null>(null)
const snapLineSeconds = ref<number | null>(null)
const menu = ref<{ noteId: string; x: number; y: number } | null>(null)
let frameHandle = 0

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
  const snap = snapToBeat((noteDrag.pointerX - rect.left - noteDrag.grabX - props.startWidthPx) / props.pixelsPerSecond)
  const y = noteDrag.pointerY - rect.top - noteDrag.grabY
  if (snap.seconds < 0 || snap.seconds > store.maxNoteSeconds) return null
  if (y < 0 || y > rect.height - NOTE_HEIGHT) return null
  return { timeSeconds: snap.seconds, y, snapped: snap.snapped }
}

// Runs every frame during a drag: the timeline can scroll under a stationary pointer, so the target is
// recomputed from the last pointer position and the current scroll offset, not only on pointer events.
function frame(): void {
  const target = dropTarget()
  noteDrag.valid = target !== null
  draft.value = target && { timeSeconds: target.timeSeconds, y: target.y }
  snapLineSeconds.value = target?.snapped ? target.timeSeconds : null
  frameHandle = requestAnimationFrame(frame)
}

function onDrop(): boolean {
  const song = store.selectedSong
  const item = noteDrag.item
  const target = dropTarget()
  if (!song || !item || !target) return false
  const pos = { timeSeconds: target.timeSeconds, y: target.y }
  if (item.id === null) {
    api.addTimelineNote(song.id, { ...pos, text: item.text, color: item.color })
    item.onDropped?.()
    return true
  }
  const note = song.timelineNotes.find((n) => n.id === item.id)
  if (!note) return false
  Object.assign(note, pos)
  api.updateTimelineNote(song.id, item.id, pos)
  return true
}

watch(
  () => noteDrag.active,
  (active) => {
    cancelAnimationFrame(frameHandle)
    draft.value = snapLineSeconds.value = null
    if (active) {
      menu.value = null
      frameHandle = requestAnimationFrame(frame)
    }
  },
)

let removeDropHandler: (() => void) | undefined
onMounted(() => (removeDropHandler = addNoteDropHandler(onDrop)))
onBeforeUnmount(() => {
  removeDropHandler?.()
  cancelAnimationFrame(frameHandle)
})

function onPress(e: PointerEvent, note: TimelineNote): void {
  const noteEl = e.currentTarget as HTMLElement
  beginNoteDrag(e, noteEl, {
    id: note.id,
    text: note.text,
    color: note.color,
    trash: {
      label: 'delete from timeline',
      run: () => store.selectedSong && api.deleteTimelineNote(store.selectedSong.id, note.id),
    },
  })
}

function onContextMenu(e: MouseEvent, note: TimelineNote): void {
  menu.value = { noteId: note.id, x: e.clientX, y: e.clientY }
}

function isDragged(note: TimelineNote): boolean {
  return noteDrag.active && noteDrag.item?.id === note.id
}

function left(seconds: number): number {
  return props.startWidthPx + seconds * props.pixelsPerSecond
}
</script>

<template>
  <div ref="layer" class="notes-layer">
    <NoteChip
      v-for="note in store.selectedSong?.timelineNotes ?? []"
      :key="note.id"
      class="timeline-note"
      :class="{ 'menu-open': menu?.noteId === note.id }"
      :text="note.text"
      :color="note.color"
      :source="isDragged(note)"
      :style="{ left: `${left(note.timeSeconds)}px`, top: `${note.y}px` }"
      @press="onPress($event, note)"
      @contextmenu.prevent="onContextMenu($event, note)"
    />
    <!-- preview of the dragged note (any source) while it hovers a valid spot -->
    <NoteChip
      v-if="noteDrag.active && noteDrag.item && draft"
      class="timeline-note preview"
      dragged
      :text="noteDrag.item.text"
      :color="noteDrag.item.color"
      :style="{ left: `${left(draft.timeSeconds)}px`, top: `${draft.y}px` }"
    />
    <div
      v-if="snapLineSeconds !== null"
      class="snap-line"
      :class="{ downbeat: props.downbeats?.includes(snapLineSeconds) }"
      :style="{ left: `${left(snapLineSeconds)}px` }" />
    <NoteContextMenu v-if="menu" kind="timeline" v-bind="menu" @close="menu = null" />
  </div>
</template>

<style scoped>
.notes-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 4;
}
.notes-layer > .timeline-note {
  position: absolute;
  pointer-events: auto;
}
.notes-layer > .timeline-note.menu-open {
  box-shadow: 0 0 6px 1px rgba(0, 229, 255, 0.25);
}
.notes-layer > .timeline-note.preview {
  pointer-events: none;
}
.snap-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  margin-left: -1px;
  background: #4d3306;
  opacity: 0.8;
  box-shadow: 0 0 6px #4d3306;
}
.snap-line.downbeat {
  background: #d9971a;
  box-shadow: 0 0 6px #d9971a;
}
</style>
