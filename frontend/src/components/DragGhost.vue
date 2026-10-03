<script setup lang="ts">
import { noteDrag } from '../store/noteDrag'
import NoteChip from './NoteChip.vue'
</script>

<template>
  <!-- follows the pointer wherever it's not over a valid timeline spot (there, the timeline shows a snapped preview) -->
  <NoteChip
    v-if="noteDrag.active && !noteDrag.valid && noteDrag.item"
    class="ghost"
    dragged
    :text="noteDrag.item.text"
    :color="noteDrag.item.color"
    :style="{ left: `${noteDrag.pointerX - noteDrag.grabX}px`, top: `${noteDrag.pointerY - noteDrag.grabY}px` }"
  />
</template>

<style scoped>
.ghost {
  position: fixed;
  z-index: 100;
  pointer-events: none;
}
</style>
