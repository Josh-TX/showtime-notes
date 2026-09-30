<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'
import { clientSettings } from '../store/clientSettings'
import { NOTE_COLORS } from '../store/noteColors'
import ColorPicker from './ColorPicker.vue'
import type { NoteColor } from '../types'

const MAX_TEXT_LENGTH = 200
const Y_STEP_PX = 16
const BEAT_EPSILON = 0.01

const store = useShowStore()

const newText = ref('')
const editText = ref('')
let saveTimer: number | undefined

const note = computed(() => store.selectedNote)
const songId = computed(() => store.selectedSong?.id ?? null)
const beats = computed(() => store.waveform?.beats ?? [])

function formatTime(seconds: number): string {
  const total = Math.floor(seconds)
  return `${Math.floor(total / 60)}:${(total % 60).toString().padStart(2, '0')}`
}

watch(
  () => store.selectedNoteId,
  () => {
    window.clearTimeout(saveTimer)
    editText.value = note.value?.text ?? ''
  },
  { immediate: true },
)

async function create(text: string, color: NoteColor): Promise<void> {
  const pos = store.selectedPosition
  if (!songId.value || !pos || !text.trim()) return
  const created = await api.addTimelineNote(songId.value, { timeSeconds: pos.timeSeconds, y: pos.y, text: text.trim(), color })
  store.selectNote(created.id)
}

async function createCustom(): Promise<void> {
  await create(newText.value, clientSettings.lastNoteColor)
  newText.value = ''
}

function onEditInput(): void {
  window.clearTimeout(saveTimer)
  const id = note.value?.id
  const sid = songId.value
  const text = editText.value.trim()
  if (!id || !sid || !text) return
  saveTimer = window.setTimeout(() => api.updateTimelineNote(sid, id, { text }), 500)
}

function patch(p: { timeSeconds?: number; y?: number; color?: NoteColor }): void {
  if (songId.value && note.value) api.updateTimelineNote(songId.value, note.value.id, p)
}

function moveTime(target: number): void {
  patch({ timeSeconds: Math.min(store.maxNoteSeconds, Math.max(0, target)) })
}

const nextBeat = computed(() => {
  const t = note.value?.timeSeconds
  return t === undefined ? undefined : beats.value.find((b) => b > t + BEAT_EPSILON)
})
const prevBeat = computed(() => {
  const t = note.value?.timeSeconds
  return t === undefined ? undefined : [...beats.value].reverse().find((b) => b < t - BEAT_EPSILON)
})

function moveY(delta: number): void {
  if (!note.value) return
  // upper bound is the timeline height, which is a sibling component's concern; the server only floors at 0
  patch({ y: Math.max(0, note.value.y + delta) })
}

async function deleteNote(): Promise<void> {
  if (!songId.value || !note.value) return
  const id = note.value.id
  store.deselect()
  await api.deleteTimelineNote(songId.value, id)
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') store.deselect()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="notes-panel">
    <div v-if="note" class="card">
      <div class="card-header">
        <span class="label">Note at {{ formatTime(note.timeSeconds) }}</span>
        <button class="link" @click="store.deselect()">de-select note</button>
      </div>
      <div class="card-body">
        <div class="section divided">
          <h4>Edit details</h4>
          <input v-model="editText" :maxlength="MAX_TEXT_LENGTH" @input="onEditInput" />
          <ColorPicker :model-value="note.color" @update:model-value="patch({ color: $event })" />
          <button class="delete" @click="deleteNote">Delete note</button>
        </div>
        <div class="section">
          <h4>Reposition</h4>
          <div class="nudge-row">
            <button :disabled="prevBeat === undefined" @click="moveTime(prevBeat!)">◀ beat</button>
            <button @click="moveTime(note.timeSeconds - 1)">◀ 1s</button>
            <button @click="moveTime(note.timeSeconds + 1)">1s ▶</button>
            <button :disabled="nextBeat === undefined" @click="moveTime(nextBeat!)">beat ▶</button>
          </div>
          <div class="nudge-row">
            <button @click="moveY(-Y_STEP_PX)">▲ up</button>
            <button @click="moveY(Y_STEP_PX)">▼ down</button>
          </div>
        </div>
      </div>
    </div>
    <div v-else-if="store.selectedPosition" class="card">
      <div class="card-header">
        <span class="label">position {{ formatTime(store.selectedPosition.timeSeconds) }} selected</span>
        <button class="link" @click="store.deselect()">de-select position</button>
      </div>
      <div class="card-body">
        <form class="section divided" @submit.prevent="createCustom">
          <h4>Create new note</h4>
          <input v-model="newText" placeholder="Note text" :maxlength="MAX_TEXT_LENGTH" />
          <ColorPicker v-model="clientSettings.lastNoteColor" />
          <button type="submit" :disabled="!newText.trim()">Create note</button>
        </form>
        <div class="section">
          <h4>Recent notes</h4>
          <div class="recents">
            <button
              v-for="(r, i) in store.show?.recentNotes ?? []"
              :key="i"
              class="recent"
              :style="{ borderLeftColor: NOTE_COLORS[r.color] }"
              @click="create(r.text, r.color)"
            >
              {{ r.text }}
            </button>
            <span v-if="!store.show?.recentNotes.length" class="hint">none yet</span>
          </div>
        </div>
      </div>
    </div>
    <span v-else class="hint">Click the timeline to select a position for a note</span>
  </div>
</template>

<style scoped>
.notes-panel {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}
.label {
  font-size: 0.85rem;
}
.card {
  border: 1px solid #333;
  border-radius: 6px;
  background: #16161a;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.35rem 0.6rem;
  border-bottom: 1px solid #333;
}
.card-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
}
.section {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.4rem;
  padding: 0.5rem 0.6rem;
  min-width: 0;
}
.section.divided {
  border-right: 1px solid #333;
}
.section input {
  align-self: stretch;
}
h4 {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #999;
}
.hint {
  font-size: 0.85rem;
  color: #777;
}
input {
  padding: 0.25rem 0.5rem;
  background: #1c1c1c;
}
.link {
  background: none;
  border: none;
  padding: 0;
  color: #00e5ff;
  font-size: 0.8rem;
  text-decoration: underline;
}
.delete {
  font-size: 0.8rem;
  padding: 0.1rem 0.6rem;
  color: #e05050;
  border-color: #5a2a2a;
}
.nudge-row {
  display: flex;
  gap: 0.3rem;
}
.nudge-row button {
  font-size: 0.8rem;
  padding: 0.1rem 0.5rem;
}
.recents {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.4rem;
  max-width: 100%;
}
.recent {
  max-width: 100%;
  height: 32px;
  padding: 0 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 1.6rem;
  color: #fff;
  background: rgba(10, 10, 12, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-left: 4px solid;
  border-radius: 0;
  user-select: none;
  box-shadow: 0 0 8px 1px #000;
}
</style>
