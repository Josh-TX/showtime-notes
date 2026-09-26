<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'

const store = useShowStore()
const includePreRoll = ref(true)
const nameInput = ref('New Recording')

const recordingSong = computed(() => store.show?.songs.find((s) => s.status === 'recording'))
const finishedSong = computed(() => store.show?.songs.find((s) => s.status === 'finished-recording'))

watch(finishedSong, (song) => {
  if (song) nameInput.value = song.name
})

async function start(): Promise<void> {
  await api.startRecording(includePreRoll.value)
}
async function stop(): Promise<void> {
  await api.stopRecording()
}
async function confirm(): Promise<void> {
  await api.confirmRecording(nameInput.value)
}
async function discard(): Promise<void> {
  await api.discardRecording()
}
</script>

<template>
  <div class="record-controls">
    <div v-if="recordingSong" class="row">
      <span class="rec-dot" /> Recording...
      <button @click="stop">Stop</button>
    </div>
    <div v-else-if="finishedSong" class="row name-form">
      <input v-model="nameInput" placeholder="Song name" />
      <button @click="confirm">Confirm &amp; Process</button>
      <button @click="discard">Discard</button>
    </div>
    <div v-else class="row">
      <label><input type="checkbox" v-model="includePreRoll" /> include pre-roll</label>
      <button @click="start">● Record</button>
    </div>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem;
}
.name-form input {
  flex: 1;
  min-width: 0;
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
