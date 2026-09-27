<script setup lang="ts">
import { api } from '../api'
import { useShowStore } from '../store/show'
import RecordControls from './RecordControls.vue'
import type { SongSummary } from '../types'

const store = useShowStore()

function select(song: SongSummary): void {
  store.selectSong(song.id)
}

async function toggleSync(song: SongSummary, event: Event): Promise<void> {
  event.stopPropagation()
  if (store.show?.sync.targetSongId === song.id) {
    await api.stopSync()
  } else {
    await api.startSync(song.id, 'acquire-sync-start')
  }
}

function statusLabel(song: SongSummary): string {
  if (song.status === 'processing') return 'processing…'
  return song.status
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
        <span v-else class="status" :class="song.status">{{ statusLabel(song) }}</span>
        <button
          v-if="['ready', 'acquiring-sync', 'synced'].includes(song.status)"
          class="sync-btn"
          @click="toggleSync(song, $event)"
        >
          {{ store.show?.sync.targetSongId === song.id ? 'unsync' : 'sync' }}
        </button>
      </div>
    </div>
    <RecordControls />
  </div>
</template>

<style scoped>
.song-menu {
  display: flex;
  flex-direction: column;
  border-right: 1px solid #333;
  overflow-y: auto;
}
.song-list {
  display: flex;
  flex-direction: column;
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
.status {
  font-size: 0.7rem;
  color: #999;
}
.status.synced {
  color: #3ecf5f;
}
.status.acquiring-sync {
  color: #e0c33e;
}
.sync-btn {
  font-size: 0.7rem;
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
