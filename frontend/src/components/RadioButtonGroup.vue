<script setup lang="ts" generic="T extends string">
defineProps<{
  options: readonly T[]
  fontSize?: string
}>()
const model = defineModel<T>({ required: true })
</script>

<template>
  <div class="radio-button-group" role="radiogroup" :style="{ fontSize: fontSize ?? '1rem' }">
    <button
      v-for="option in options"
      :key="option"
      type="button"
      role="radio"
      :aria-checked="model === option"
      :class="{ selected: model === option }"
      @click="model = option"
    >
      {{ option }}
    </button>
  </div>
</template>

<style scoped>
/* all sizes in em so the whole group scales with the fontSize input */
.radio-button-group {
  display: inline-flex;
}
button {
  font-size: 1em;
  padding: 0.2em 0.7em;
  line-height: 1.2;
  border: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  background: #1c1d21;
  color: inherit;
  cursor: pointer;
}
button + button {
  border-left: 1px solid #2a2a2a;
}
button:hover {
  background: #26272c;
}
button.selected {
  border-bottom-color: #3b82f6;
}
</style>
