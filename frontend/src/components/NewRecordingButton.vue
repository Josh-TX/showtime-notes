<script setup lang="ts">
import { computed } from 'vue'
import { useShowStore } from '../store/show'

const store = useShowStore()

const recordingSong = computed(() => store.show?.songs.find((s) => s.status === 'recording'))
const disabled = computed(() => !!recordingSong.value || store.isStartingRecording)
</script>

<template>
  <div class="record-controls">
    <button class="text-btn" :disabled="disabled" @click="store.openStartRecording()">New recording</button>
  </div>
</template>

<style scoped>
.record-controls {
  display: flex;
  justify-content: flex-end;
  padding: 0.5rem;
  border-top: 1px solid #2a2a2a;
}
.text-btn {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0.3rem 0.5rem;
  font-size: 0.85rem;
}
.text-btn:disabled {
  color: #666;
  cursor: default;
}
</style>
