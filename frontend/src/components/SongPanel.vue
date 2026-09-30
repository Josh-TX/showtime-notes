<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'
import SyncArrows from './SyncArrows.vue'
import NotesPanel from './NotesPanel.vue'

const LIVE_PEAKS_PER_SECOND = 20

const store = useShowStore()
const freeNotes = ref('')
const recordingName = ref('')
let saveTimer: number | undefined

const newRecordingName = ref('')

watch(
  () => store.isStartingRecording,
  (isStarting) => {
    if (isStarting) newRecordingName.value = ''
  },
)

async function startNewRecording(includePreRoll: boolean): Promise<void> {
  await api.startRecording(includePreRoll, newRecordingName.value.trim())
}

function cancelNewRecording(): void {
  store.cancelStartRecording()
}

watch(
  () => store.selectedSong?.id,
  () => {
    freeNotes.value = store.selectedSong?.freeNotes ?? ''
    recordingName.value = store.selectedSong?.name ?? ''
  },
  { immediate: true },
)

function onInput(): void {
  window.clearTimeout(saveTimer)
  const songId = store.selectedSong?.id
  if (!songId) return
  saveTimer = window.setTimeout(() => {
    api.setFreeNotes(songId, freeNotes.value)
  }, 500)
}

const elapsed = computed(() => {
  const total = Math.floor(store.recordingPeaks.length / LIVE_PEAKS_PER_SECOND)
  const mm = Math.floor(total / 60)
  const ss = total % 60
  return `${mm}:${ss.toString().padStart(2, '0')}`
})

async function stopAndSave(): Promise<void> {
  if (!recordingName.value.trim()) return
  await api.stopAndSaveRecording(recordingName.value.trim())
}

async function stopAndDiscard(): Promise<void> {
  if (!window.confirm('Discard this recording? This cannot be undone.')) return
  await api.stopAndDiscardRecording()
}

async function deleteSong(): Promise<void> {
  const song = store.selectedSong
  if (!song) return
  if (!window.confirm(`Delete "${song.name}"? This cannot be undone.`)) return
  await api.deleteSong(song.id)
}

const isSynced = computed(() => store.show?.sync.targetSongId === store.selectedSong?.id)
const syncPhase = computed(() => (isSynced.value ? store.show?.sync.phase ?? null : null))
const syncColor = computed(() => (syncPhase.value === 'tracking' ? '#3ecf5f' : '#e0c33e'))

async function toggleSync(): Promise<void> {
  const song = store.selectedSong
  if (!song) return
  if (isSynced.value) {
    await api.stopSync()
  } else {
    await api.startSync(song.id, 'acquire-sync-start')
  }
}
</script>

<template>
  <div class="song-panel" v-if="store.isStartingRecording">
    <div class="title-row">
      <h2>Start new recording</h2>
      <button class="cancel-btn" @click="cancelNewRecording">Cancel</button>
    </div>
    <input v-model="newRecordingName" class="name-input" placeholder="Song Name" />
    <div class="recording-actions">
      <button @click="startNewRecording(false)">Start recording now</button>
      <button @click="startNewRecording(true)">Start recording 1 second ago</button>
    </div>
  </div>
  <div class="song-panel" v-else-if="store.selectedSong">
    <template v-if="store.selectedSong.status === 'recording'">
      <div class="recording-header">
        <span class="rec-dot" />
        <input v-model="recordingName" class="name-input" placeholder="Recording name" />
        <span class="elapsed">{{ elapsed }}</span>
      </div>
      <div class="recording-actions">
        <button :disabled="!recordingName.trim()" @click="stopAndSave">Stop &amp; Save</button>
        <button @click="stopAndDiscard">Stop &amp; Discard</button>
      </div>
    </template>
    <template v-else>
      <div class="title-row">
        <h2>{{ store.selectedSong.name }}</h2>
        <button class="delete-btn" @click="deleteSong">Delete</button>
      </div>
      <div v-if="['ready', 'syncing'].includes(store.selectedSong.status)" class="sync-row">
        <button class="sync-btn" @click="toggleSync">
          {{ isSynced ? 'Unsync' : 'Sync' }}
        </button>
        <template v-if="isSynced">
          <SyncArrows :color="syncColor" :size="16" />
          <span class="phase-badge" :style="{ color: syncColor, borderColor: syncColor }">
            {{ syncPhase === 'tracking' ? 'Tracking' : 'Acquiring' }}
          </span>
        </template>
      </div>
    </template>
    <p v-if="store.selectedSong.status === 'processing'">
      Processing… {{ Math.round((store.selectedSong.processingProgress ?? 0) * 100) }}%
    </p>
    <p v-if="store.selectedSong.processingError" class="error">{{ store.selectedSong.processingError }}</p>
    <textarea v-model="freeNotes" placeholder="Free notes for this song…" @input="onInput" />
    <NotesPanel v-if="['recording', 'ready', 'syncing'].includes(store.selectedSong.status)" />
  </div>
  <div class="song-panel empty" v-else>Select a song</div>
</template>

<style scoped>
.song-panel {
  display: flex;
  flex-direction: column;
  padding: 0.5rem 1rem;
  overflow-y: auto;
}
.song-panel.empty {
  color: #777;
}
h2 {
  margin: 0 0 0.4rem;
  font-size: 1.1rem;
}
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.title-row h2 {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.delete-btn {
  flex-shrink: 0;
  font-size: 0.8rem;
  padding: 0.2rem 0.6rem;
  color: #e05050;
  border-color: #5a2a2a;
}
.cancel-btn {
  flex-shrink: 0;
  font-size: 0.8rem;
  padding: 0.2rem 0.6rem;
}
.sync-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
}
.sync-btn {
  flex-shrink: 0;
  font-size: 0.8rem;
  padding: 0.2rem 0.6rem;
}
.phase-badge {
  flex-shrink: 0;
  font-size: 0.75rem;
  padding: 0.1rem 0.5rem;
  border: 1px solid;
  border-radius: 1rem;
}
textarea {
  flex: none;
  height: 64px;
  margin-bottom: 0.5rem;
  resize: none;
  background: #1c1c1c;
  color: inherit;
  border: 1px solid #333;
  padding: 0.5rem;
}
.error {
  color: #e05050;
}
.recording-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
}
.name-input {
  flex-shrink: 0;
  font-size: 1.1rem;
  background: #1c1c1c;
  color: inherit;
  border: 1px solid #333;
  padding: 0.3rem 0.5rem;
  margin-bottom: 0.5rem;
}
.recording-header .name-input {
  flex: 1;
}
.elapsed {
  font-family: monospace;
  color: #ccc;
}
.recording-actions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.6rem;
}
.rec-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e04040;
  flex-shrink: 0;
  animation: pulse 1s infinite;
}
@keyframes pulse {
  50% {
    opacity: 0.3;
  }
}
</style>
