<script setup lang="ts">
import { computed } from 'vue'
import { useShowStore } from '../store/show'

const store = useShowStore()

const color = computed(() => {
  switch (store.show?.sync.status) {
    case 'synced':
      return '#3ecf5f'
    case 'acquiring-sync':
      return '#e0c33e'
    default:
      return '#666'
  }
})

const targetName = computed(() => {
  const id = store.show?.sync.targetSongId
  return id ? store.show?.songs.find((s) => s.id === id)?.name : null
})
</script>

<template>
  <div class="sync-indicator" :title="targetName ? `Synced with: ${targetName}` : 'Not synced'">
    <svg width="20" height="20" viewBox="0 0 24 24" :fill="color">
      <path d="M2 7h16l-4-4 1.4-1.4L22 9l-6.6 6.4L14 14l4-4H2z" />
    </svg>
    <svg width="20" height="20" viewBox="0 0 24 24" :fill="color">
      <path d="M22 17H6l4 4-1.4 1.4L2 15l6.6-6.4L10 10l-4 4h16z" />
    </svg>
    <span v-if="targetName" class="target-name">{{ targetName }}</span>
  </div>
</template>

<style scoped>
.sync-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  line-height: 0.7;
}
.target-name {
  font-size: 0.65rem;
  line-height: 1;
  margin-top: 2px;
  color: #ccc;
}
</style>
