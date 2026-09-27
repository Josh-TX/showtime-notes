<script setup lang="ts">
withDefaults(defineProps<{ color: string; size?: number }>(), {
  size: 20,
})
</script>

<template>
  <div class="arrows" :style="{ gap: `${Math.max(1, Math.round(size / 20))}px` }">
    <svg :width="size" :height="(size * 11) / 24" viewBox="0 -0.5 24 11" :fill="color">
      <path d="M0 3.5H14V-0.5L24 5L14 10.5V6.5H0Z" />
    </svg>
    <svg :width="size" :height="(size * 11) / 24" viewBox="0 -0.5 24 11" :fill="color">
      <path d="M24 3.5H10V-0.5L0 5L10 10.5V6.5H24Z" />
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
