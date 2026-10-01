<script setup lang="ts">
defineProps<{
  label: string
  fontSize?: string
  disabled?: boolean
}>()
const model = defineModel<boolean>({ required: true })
</script>

<template>
  <label class="checkbox-input" :class="{ disabled }" :style="{ fontSize: fontSize ?? '1rem' }">
    <input type="checkbox" v-model="model" :disabled="disabled" />
    {{ label }}
  </label>
</template>

<style scoped>
/* all sizes in em so the control scales with the fontSize input */
.checkbox-input {
  display: inline-flex;
  align-items: center;
  gap: 0.4em;
  padding: 0.2em 0.7em;
  line-height: 1.2;
  /* invisible, matches RadioButtonGroup's selected-indicator border so heights line up */
  border-bottom: 2px solid transparent;
  background: #1c1d21;
  cursor: pointer;
  user-select: none;
}
.checkbox-input:hover:not(.disabled) {
  background: #26272c;
}
.checkbox-input.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
input {
  margin: 0;
  width: 1em;
  height: 1em;
}
</style>
