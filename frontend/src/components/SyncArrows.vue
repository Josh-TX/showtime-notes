<script setup lang="ts">
withDefaults(defineProps<{ color: string; size?: number }>(), {
  size: 20,
})
</script>

<template>
  <div class="arrows" :style="{ gap: `${Math.max(1, Math.round(size / 20))}px` }">
    <svg :width="size" :height="(size * 9) / 20" viewBox="0 0 24 10" :fill="color">
      <path d="M0 3.5H14V0L24 5L14 10V6.5H0Z" />
    </svg>
    <svg :width="size" :height="(size * 9) / 20" viewBox="0 0 24 10" :fill="color">
      <path d="M24 3.5H10V0L0 5L10 10V6.5H24Z" />
    </svg>
  </div>
</template>

<style scoped>
.arrows {
  display: flex;
  flex-direction: column;
  align-items: center;
}
</style>
