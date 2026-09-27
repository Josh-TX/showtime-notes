<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'

const store = useShowStore()
const includePreRoll = ref(true)

const recordingSong = computed(() => store.show?.songs.find((s) => s.status === 'recording'))

async function start(): Promise<void> {
  await api.startRecording(includePreRoll.value)
}
</script>

<template>
  <div v-if="!recordingSong" class="record-controls row">
    <label><input type="checkbox" v-model="includePreRoll" /> include pre-roll</label>
    <button @click="start">● Record</button>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem;
  border-top: 1px solid #2a2a2a;
}
</style>
