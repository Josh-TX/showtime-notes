<script setup lang="ts">
import { computed } from 'vue'
import { useShowStore } from '../store/show'
import SyncArrows from './SyncArrows.vue'

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

const targetId = computed(() => store.show?.sync.targetSongId ?? null)
const targetName = computed(() => {
  const id = targetId.value
  return id ? store.show?.songs.find((s) => s.id === id)?.name : null
})

function selectSyncedSong(): void {
  if (targetId.value) store.selectSong(targetId.value)
}
</script>

<template>
  <div
    class="sync-indicator"
    :class="{ clickable: !!targetId }"
    :role="targetId ? 'button' : undefined"
    :tabindex="targetId ? 0 : undefined"
    :title="targetName ? `Synced with: ${targetName}` : 'Not synced'"
    @click="selectSyncedSong"
    @keydown.enter="selectSyncedSong"
  >
    <SyncArrows :color="color" :size="14" />
    <span v-if="targetName" class="target-name">{{ targetName }}</span>
  </div>
</template>

<style scoped>
.sync-indicator {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  align-self: stretch;
  margin: -0.4rem 0;
  padding: 0.4rem 0.6rem;
}
.sync-indicator.clickable {
  cursor: pointer;
}
.sync-indicator.clickable:hover {
  background: #262626;
}
.target-name {
  font-size: 0.9rem;
  line-height: 1;
  color: #ccc;
}
</style>
