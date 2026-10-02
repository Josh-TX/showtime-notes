<script setup lang="ts">
import { NOTE_COLORS } from '../store/noteColors'
import type { NoteColor } from '../types'

// The note's look: colored left edge, uppercase text. The whole chip is the drag source (emits press).
// Sizing/positioning is up to the parent.
defineProps<{ text: string; color: NoteColor; dragging?: boolean; invalid?: boolean }>()
defineEmits<{ press: [e: PointerEvent] }>()
</script>

<template>
  <div
    class="note-chip"
    :class="{ dragging, invalid }"
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
.note-chip.dragging {
  cursor: grabbing;
}
.note-chip.invalid {
  opacity: 0.4;
  cursor: not-allowed;
}
.note-chip.dragging {
  box-shadow: 0 0 6px 1px rgba(0, 229, 255, 0.25);
  z-index: 1;
}
</style>
