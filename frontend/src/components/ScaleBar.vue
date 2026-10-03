<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ pixelsPerSecond: number; bottomOffsetPx: number }>()

const MAX_BAR_PX = 200
const UNITS_MS = [100, 200, 500, 1000, 2000, 5000, 10000, 30000, 60000]

function formatUnit(ms: number): string {
  if (ms >= 60000) return `${ms / 60000} min`
  if (ms >= 1000) return `${ms / 1000} s`
  return `${ms} ms`
}

const unit = computed(() => {
  const fitting = UNITS_MS.filter((ms) => (ms / 1000) * props.pixelsPerSecond <= MAX_BAR_PX)
  return fitting.length ? fitting[fitting.length - 1] : UNITS_MS[0]
})
const barWidthPx = computed(() => (unit.value / 1000) * props.pixelsPerSecond)
</script>

<template>
  <div class="scale-bar" :style="{ bottom: `${bottomOffsetPx + 4}px` }">
    <span class="label">{{ formatUnit(unit) }}</span>
    <div class="bar" :style="{ width: `${barWidthPx}px` }"></div>
  </div>
</template>

<style scoped>
.scale-bar {
  position: absolute;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  z-index: 10;
  pointer-events: none;
  font-size: 12px;
  line-height: 1;
  color: #fff;
  text-shadow: 0 0 3px #000, 0 0 3px #000;
}
.bar {
  height: 6px;
  border: 2px solid #fff;
  border-top: none;
  box-sizing: border-box;
  filter: drop-shadow(0 0 2px #000);
}
</style>
