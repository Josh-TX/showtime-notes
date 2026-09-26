<script setup lang="ts">
import { ref, watch } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'

const store = useShowStore()
const freeNotes = ref('')
let saveTimer: number | undefined

watch(
  () => store.selectedSong?.id,
  () => {
    freeNotes.value = store.selectedSong?.freeNotes ?? ''
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
</script>

<template>
  <div class="song-panel" v-if="store.selectedSong">
    <h2>{{ store.selectedSong.name }}</h2>
    <p v-if="store.selectedSong.status === 'processing'">
      Processing… {{ Math.round((store.selectedSong.processingProgress ?? 0) * 100) }}%
    </p>
    <p v-if="store.selectedSong.processingError" class="error">{{ store.selectedSong.processingError }}</p>
    <textarea v-model="freeNotes" placeholder="Free notes for this song…" @input="onInput" />
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
textarea {
  flex: 1;
  resize: none;
  background: #1c1c1c;
  color: inherit;
  border: 1px solid #333;
  padding: 0.5rem;
  min-height: 120px;
}
.error {
  color: #e05050;
}
</style>
