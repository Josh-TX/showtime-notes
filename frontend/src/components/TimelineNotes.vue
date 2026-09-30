<script setup lang="ts">
import { useShowStore } from '../store/show'
import { NOTE_COLORS } from '../store/noteColors'

// Notes + selected-position marker, overlaid on a timeline whose t=0 sits at startWidthPx.
const props = defineProps<{ startWidthPx: number; pixelsPerSecond: number }>()

const store = useShowStore()

function left(seconds: number): number {
  return props.startWidthPx + seconds * props.pixelsPerSecond
}
</script>

<template>
  <div class="notes-layer">
    <div
      v-for="note in store.selectedSong?.timelineNotes ?? []"
      :key="note.id"
      class="timeline-note"
      :class="{ selected: note.id === store.selectedNoteId }"
      :style="{ left: `${left(note.timeSeconds)}px`, top: `${note.y}px`, borderLeftColor: NOTE_COLORS[note.color] }"
      @click.stop="store.selectedNoteId === note.id ? store.deselect() : store.selectNote(note.id)"
    >
      {{ note.text }}
    </div>
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
  padding: 0 8px;
  max-width: 800px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 1.6rem;
  color: #fff;
  background: rgba(10, 10, 12, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-left: 4px solid;
  box-shadow: 0 0 8px 1px #000;
  pointer-events: auto;
  cursor: pointer;
  user-select: none;
}
.timeline-note.selected {
  box-shadow: 0 0 0 1px #00e5ff, 0 0 8px #00e5ff;
  z-index: 1;
}
.position-marker {
  position: absolute;
  width: 1px;
  height: 32px;
  background: #00e5ff;
  box-shadow: 0 0 6px 1px #00e5ff;
}
</style>
