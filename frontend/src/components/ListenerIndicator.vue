<script setup lang="ts">
import { computed } from 'vue'
import { useShowStore } from '../store/show'

const store = useShowStore()
const listenerLabel = computed(() =>
  store.show?.listener.deviceName ? `${store.show.listener.deviceName} is the listener` : 'server has no listener',
)
</script>

<template>
  <div class="listener-indicator" role="button" tabindex="0">
    <div class="listener-label">{{ listenerLabel }}</div>
    <div class="loudness-meter" title="Live loudness">
      <div class="loudness-fill" :style="{ width: `${Math.round(store.loudness * 100)}%` }" />
    </div>
  </div>
</template>

<style scoped>
.listener-indicator {
  display: flex;
  flex-direction: column;
  width: 220px;
  padding: 0.15rem 0.6rem;
  cursor: pointer;
}
.listener-indicator:hover {
  background: #262626;
}
.listener-label {
  font-size: 0.95rem;
  color: #ccc;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.loudness-meter {
  margin-top: 0.15rem;
  width: 100%;
  height: 4px;
  background: #333;
  border-radius: 2px;
  overflow: hidden;
}
.loudness-fill {
  height: 100%;
  background: #3ecf5f;
}
</style>
