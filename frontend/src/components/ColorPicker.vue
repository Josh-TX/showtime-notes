<script setup lang="ts">
import type { NoteColor } from '../types'
import { NOTE_COLORS, NOTE_COLOR_NAMES } from '../store/noteColors'

defineProps<{ modelValue: NoteColor }>()
defineEmits<{ 'update:modelValue': [color: NoteColor] }>()
</script>

<template>
  <div class="color-picker">
    <button
      v-for="name in NOTE_COLOR_NAMES"
      :key="name"
      type="button"
      class="swatch"
      :class="{ selected: name === modelValue }"
      :style="{ background: NOTE_COLORS[name] }"
      :title="name"
      @click="$emit('update:modelValue', name)"
    />
  </div>
</template>

<style scoped>
.color-picker {
  display: grid;
  grid-template-columns: repeat(8, 18px);
  gap: 6px;
}
.swatch {
  width: 18px;
  height: 18px;
  padding: 0;
  border: none;
  border-radius: 3px;
}
.swatch:hover:not(:disabled) {
  filter: brightness(1.15);
}
.swatch.selected {
  box-shadow: 0 0 0 1px #00e5ff, 0 0 6px #00e5ff;
}
</style>
