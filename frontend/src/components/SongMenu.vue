<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'
import SyncArrows from './SyncArrows.vue'
import ProcessingGears from './ProcessingGears.vue'
import type { SongSummary } from '../types'

const store = useShowStore()

function select(song: SongSummary): void {
  store.selectSong(song.id)
}

const listEl = ref<HTMLElement | null>(null)
const dragId = ref<string | null>(null)
const overId = ref<string | null>(null)
const overAfter = ref(false)
const ghost = ref({ x: 0, y: 0, w: 0, h: 0, grabX: 0, grabY: 0 })
const dragSong = computed(() => store.show?.songs.find((s) => s.id === dragId.value) ?? null)

// Pointer-based reorder (like note drag): native HTML5 drag is blocked globally.
function startDrag(e: PointerEvent, song: SongSummary): void {
  if (e.button !== 0) return
  e.preventDefault()
  dragId.value = song.id
  const r = (e.currentTarget as HTMLElement).closest('.song-row')!.getBoundingClientRect()
  ghost.value = { x: e.clientX, y: e.clientY, w: r.width, h: r.height, grabX: e.clientX - r.left, grabY: e.clientY - r.top }
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', endDrag)
  window.addEventListener('keydown', onKeyDown)
}

function onPointerMove(e: PointerEvent): void {
  ghost.value.x = e.clientX
  ghost.value.y = e.clientY
  const rows = listEl.value?.querySelectorAll<HTMLElement>('.song-row') ?? []
  overId.value = null
  for (const row of rows) {
    const r = row.getBoundingClientRect()
    if (e.clientY >= r.top && e.clientY < r.bottom) {
      overId.value = row.dataset.id ?? null
      overAfter.value = e.clientY > r.top + r.height / 2
      return
    }
  }
}

function onKeyDown(e: KeyboardEvent): void {
  if (e.key === 'Escape') endDrag()
}

function endDrag(): void {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', endDrag)
  window.removeEventListener('keydown', onKeyDown)
  dragId.value = overId.value = null
}

function onPointerUp(): void {
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
    <div ref="listEl" class="song-list" :class="{ reordering: dragId }">
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
        :data-id="song.id"
      >
        <div class="song-main" @click="select(song)">
          <span v-if="song.name" class="name">{{ song.name }}</span>
          <span v-else class="name untitled">(untitled song)</span>
          <span v-if="song.status === 'recording'" class="rec-dot" />
          <ProcessingGears v-else-if="song.status === 'processing'" :size="16" />
          <SyncArrows v-else-if="song.id === store.show?.sync.targetSongId" :color="targetSyncColor()" :size="16" />
        </div>
        <span class="drag-handle" title="Drag to reorder" @pointerdown="startDrag($event, song)">⠿</span>
      </div>
    </div>
    <div
      v-if="dragSong"
      class="song-row ghost"
      :class="{ selected: dragSong.id === store.selectedSongId }"
      :style="{ left: ghost.x - ghost.grabX + 'px', top: ghost.y - ghost.grabY + 'px', width: ghost.w + 'px', height: ghost.h + 'px' }"
    >
      <div class="song-main">
        <span v-if="dragSong.name" class="name">{{ dragSong.name }}</span>
        <span v-else class="name untitled">(untitled song)</span>
      </div>
      <span class="drag-handle">⠿</span>
    </div>
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
  position: relative;
  display: flex;
  align-items: stretch;
  border-bottom: 1px solid #2a2a2a;
}
.song-row.selected {
  background: #26374a;
}
.song-main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0 0.5rem 0.5rem;
  cursor: pointer;
}
.song-list:not(.reordering) .song-row:not(.selected) .song-main:hover {
  background: #2a2a2a;
}
.song-row.ghost {
  position: fixed;
  pointer-events: none;
  z-index: 1000;
  box-sizing: border-box;
  background: rgba(17, 17, 17, 0.5);
  border: 1px solid rgba(68, 68, 68, 0.5);
}
.song-row.ghost.selected {
  background: rgba(38, 55, 74, 0.5);
}
.song-row.dragging {
  opacity: 0.4;
}
.song-row.drop-before::before,
.song-row.drop-after::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: #6aa9ff;
  z-index: 1;
}
.song-row.drop-before::before {
  top: 0;
}
.song-row.drop-after::after {
  bottom: 0;
}
.drag-handle {
  cursor: grab;
  color: #888;
  padding: 0 0.5rem 0 7px;
  display: flex;
  align-items: center;
  user-select: none;
  touch-action: none;
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
.untitled {
  color: #777;
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
