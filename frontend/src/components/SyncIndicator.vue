<script setup lang="ts">
import { computed } from 'vue'
import { useShowStore } from '../store/show'
import SyncArrows from './SyncArrows.vue'

const store = useShowStore()

const color = computed(() => {
  if (store.show?.sync.status !== 'syncing') return '#666'
  return store.show.sync.phase === 'tracking' ? '#3ecf5f' : '#e0c33e'
})

const targetId = computed(() => store.show?.sync.targetSongId ?? null)
const targetName = computed(() => {
  const id = targetId.value
  return id ? store.show?.songs.find((s) => s.id === id)?.name : null
})
const statusTitle = computed(() => {
  if (!targetName.value) return 'Not synced'
  return store.show?.sync.phase === 'tracking' ? `Synced with: ${targetName.value}` : `Acquiring sync with: ${targetName.value}`
})

function selectSyncedSong(): void {
  const id = targetId.value
  if (!id) return
  store.selectSong(id)
  document.querySelector(`.song-row[data-id="${id}"]`)?.scrollIntoView({ block: 'nearest' })
}
</script>

<template>
  <div
    class="sync-indicator"
    :class="{ clickable: !!targetId }"
    :role="targetId ? 'button' : undefined"
    :tabindex="targetId ? 0 : undefined"
    :title="statusTitle"
    @click="selectSyncedSong"
    @keydown.enter="selectSyncedSong"
  >
    <SyncArrows :color="color" :size="16" />
    <span class="target-name">{{ targetName ?? 'nothing synced' }}</span>
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
