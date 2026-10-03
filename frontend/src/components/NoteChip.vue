<script setup lang="ts">
import { NOTE_COLORS } from '../store/noteColors'
import type { NoteColor } from '../types'

// The note's look: colored left edge, uppercase text. The whole chip is the drag source (emits press).
// source = dimmed copy left in place while its note is dragged; dragged = the slightly see-through note being carried.
// Sizing/positioning is up to the parent.
defineProps<{ text: string; color: NoteColor; source?: boolean; dragged?: boolean }>()
defineEmits<{ press: [e: PointerEvent] }>()
</script>

<template>
  <div
    class="note-chip"
    :class="{ source, dragged }"
    :style="{ borderColor: NOTE_COLORS[color] }"
    @pointerdown="$emit('press', $event)"
  >
    <span class="text">{{ text }}</span>
  </div>
</template>

<style scoped>
.note-chip {
  position: relative;
  height: 32px;
  line-height: 30px;
  padding: 0 8px;
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
  user-select: none;
  cursor: grab;
  touch-action: none;
}
.text {
  overflow: hidden;
  text-overflow: ellipsis;
}
.note-chip.source {
  opacity: 0.2;
}
.note-chip.dragged {
  opacity: 0.85;
}
</style>
