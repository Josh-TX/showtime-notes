<script setup lang="ts">
import { useShowStore } from '../store/show'
import NewRecordingButton from './NewRecordingButton.vue'
import SyncArrows from './SyncArrows.vue'
import ProcessingGears from './ProcessingGears.vue'
import type { SongSummary } from '../types'

const store = useShowStore()

function select(song: SongSummary): void {
  store.selectSong(song.id)
}

function targetSyncColor(): string {
  return store.show?.sync.phase === 'tracking' ? '#3ecf5f' : '#e0c33e'
}
</script>

<template>
  <div class="song-menu">
    <div class="song-list">
      <div
        v-for="song in store.show?.songs ?? []"
        :key="song.id"
        class="song-row"
        :class="{ selected: song.id === store.selectedSongId }"
        @click="select(song)"
      >
        <span class="name">{{ song.name }}</span>
        <span v-if="song.status === 'recording'" class="rec-dot" />
        <ProcessingGears v-else-if="song.status === 'processing'" :size="16" />
        <SyncArrows v-else-if="song.id === store.show?.sync.targetSongId" :color="targetSyncColor()" :size="16" />
      </div>
    </div>
    <NewRecordingButton />
  </div>
</template>

<style scoped>
.song-menu {
  display: flex;
  flex-direction: column;
  border-right: 1px solid #333;
  overflow: hidden;
}
.song-list {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow-y: auto;
}
.song-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem;
  cursor: pointer;
  border-bottom: 1px solid #2a2a2a;
}
.song-row.selected {
  background: #26374a;
}
.song-row:hover {
  background: #2a2a2a;
}
.name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rec-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e04040;
  display: inline-block;
  animation: pulse 1s infinite;
}
@keyframes pulse {
  50% {
    opacity: 0.3;
  }
}
</style>
