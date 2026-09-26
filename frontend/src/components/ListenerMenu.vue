<script setup lang="ts">
import { ref } from 'vue'
import { useShowStore } from '../store/show'
import { startCapture, stopCapture } from '../audio/capture'
import { startPlayback, stopPlayback, pushPlaybackChunk } from '../audio/playback'
import { ws } from '../ws'

const store = useShowStore()
const open = ref(false)

async function toggleListener(): Promise<void> {
  if (store.isListener) {
    stopCapture()
    store.releaseListener()
  } else {
    await startCapture()
    store.becomeListener()
  }
}

async function toggleLiveAudio(): Promise<void> {
  if (store.wantsLiveAudio) {
    store.setLiveAudioSubscription(false)
    stopPlayback()
    ws.offBinary(pushPlaybackChunk)
  } else {
    await startPlayback()
    ws.onBinary(pushPlaybackChunk)
    store.setLiveAudioSubscription(true)
  }
}
</script>

<template>
  <div class="listener-menu">
    <div class="loudness-meter" title="Live loudness">
      <div class="loudness-fill" :style="{ width: `${Math.round(store.loudness * 100)}%` }" />
    </div>
    <button class="menu-toggle" @click="open = !open">
      {{ store.show?.listener.deviceName ?? 'no listener' }} ▾
    </button>
    <div v-if="open" class="dropdown" @click.self="open = false">
      <button @click="toggleListener">
        {{ store.isListener ? 'Stop streaming as listener' : 'Become the listener' }}
      </button>
      <button @click="toggleLiveAudio">
        {{ store.wantsLiveAudio ? 'Stop playing live audio' : 'Play live audio' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.listener-menu {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.loudness-meter {
  width: 60px;
  height: 8px;
  background: #333;
  border-radius: 4px;
  overflow: hidden;
}
.loudness-fill {
  height: 100%;
  background: #3ecf5f;
}
.menu-toggle {
  background: none;
  border: 1px solid #555;
  color: inherit;
  border-radius: 4px;
  padding: 0.2rem 0.5rem;
}
.dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  background: #222;
  border: 1px solid #444;
  display: flex;
  flex-direction: column;
  min-width: 200px;
  z-index: 20;
}
.dropdown button {
  text-align: left;
  padding: 0.5rem;
  background: none;
  border: none;
  color: inherit;
}
.dropdown button:hover {
  background: #333;
}
</style>
