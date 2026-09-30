<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'
import NewRecordingButton from './NewRecordingButton.vue'
import SyncArrows from './SyncArrows.vue'
import ProcessingGears from './ProcessingGears.vue'
import type { SongSummary } from '../types'

const store = useShowStore()

function select(song: SongSummary): void {
  store.selectSong(song.id)
}

const armedId = ref<string | null>(null)
const dragId = ref<string | null>(null)
const overId = ref<string | null>(null)
const overAfter = ref(false)

function onDragStart(e: DragEvent, song: SongSummary): void {
  dragId.value = song.id
  e.dataTransfer!.effectAllowed = 'move'
  e.dataTransfer!.setData('text/plain', song.id)
  const row = e.currentTarget as HTMLElement
  const ghost = row.cloneNode(true) as HTMLElement
  const bg = row.classList.contains('selected') ? '38,55,74' : '17,17,17'
  ghost.style.cssText = `position:fixed;top:-1000px;width:${row.offsetWidth}px;background:rgba(${bg},0.6);`
  document.body.appendChild(ghost)
  e.dataTransfer!.setDragImage(ghost, e.clientX - row.getBoundingClientRect().left, e.clientY - row.getBoundingClientRect().top)
  setTimeout(() => ghost.remove())
}

function onDragOver(e: DragEvent, song: SongSummary): void {
  if (!dragId.value) return
  e.preventDefault()
  const r = (e.currentTarget as HTMLElement).getBoundingClientRect()
  overId.value = song.id
  overAfter.value = e.clientY > r.top + r.height / 2
}

function endDrag(): void {
  armedId.value = dragId.value = overId.value = null
}

function onDrop(): void {
  const from = dragId.value
  const target = overId.value
  const after = overAfter.value
  endDrag()
  if (!from || !target || !store.show) return
  const ids = store.show.songs.map((s) => s.id).filter((id) => id !== from)
  const idx = ids.indexOf(target)
  if (idx < 0) return
  ids.splice(after ? idx + 1 : idx, 0, from)
  if (ids.every((id, i) => id === store.show!.songs[i].id)) return
  const byId = new Map(store.show.songs.map((s) => [s.id, s]))
  store.show.songs = ids.map((id) => byId.get(id)!)
  api.reorderSongs(ids)
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
        :class="{
          selected: song.id === store.selectedSongId,
          dragging: song.id === dragId,
          'drop-before': song.id === overId && !overAfter && dragId !== song.id,
          'drop-after': song.id === overId && overAfter && dragId !== song.id,
        }"
        :draggable="armedId === song.id"
        @click="select(song)"
        @dragstart="onDragStart($event, song)"
        @dragover="onDragOver($event, song)"
        @drop.prevent="onDrop"
        @dragend="endDrag"
      >
        <span class="name">{{ song.name }}</span>
        <span v-if="song.status === 'recording'" class="rec-dot" />
        <ProcessingGears v-else-if="song.status === 'processing'" :size="16" />
        <SyncArrows v-else-if="song.id === store.show?.sync.targetSongId" :color="targetSyncColor()" :size="16" />
        <span
          class="drag-handle"
          title="Drag to reorder"
          @mousedown="armedId = song.id"
          @mouseup="armedId = null"
          @click.stop
          >⠿</span
        >
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
  padding: 0.5rem 0 0.5rem 0.5rem;
  cursor: pointer;
  border-bottom: 1px solid #2a2a2a;
}
.song-row.selected {
  background: #26374a;
}
.song-row:hover {
  background: #2a2a2a;
}
.song-row.dragging {
  opacity: 0.4;
}
.song-row.drop-before {
  box-shadow: inset 0 2px 0 #6aa9ff;
}
.song-row.drop-after {
  box-shadow: inset 0 -2px 0 #6aa9ff;
}
.drag-handle {
  cursor: grab;
  color: #888;
  padding: 0 0.5rem 0 0.25rem;
  margin: -0.5rem 0;
  align-self: stretch;
  display: flex;
  align-items: center;
  user-select: none;
}
.drag-handle:hover {
  color: #ddd;
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
