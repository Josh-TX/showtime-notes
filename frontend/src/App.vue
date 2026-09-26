<script setup lang="ts">
import { ref } from 'vue'
import Navbar from './components/Navbar.vue'
import SongMenu from './components/SongMenu.vue'
import SongPanel from './components/SongPanel.vue'
import Track from './components/Track.vue'
import { useShowStore } from './store/show'

const DEVICE_NAME_STORAGE_KEY = 'deviceName'

const store = useShowStore()
const deviceNameInput = ref('')

const storedDeviceName = localStorage.getItem(DEVICE_NAME_STORAGE_KEY)
if (storedDeviceName) store.connect(storedDeviceName)

function join(): void {
  const deviceName = deviceNameInput.value.trim()
  if (!deviceName) return
  localStorage.setItem(DEVICE_NAME_STORAGE_KEY, deviceName)
  store.connect(deviceName)
}
</script>

<template>
  <div v-if="!store.connected" class="join-gate">
    <form @submit.prevent="join">
      <h1>Showtime Notes</h1>
      <label for="device-name">Device Name</label>
      <input id="device-name" v-model="deviceNameInput" autofocus />
      <button type="submit">Join</button>
    </form>
  </div>
  <div v-else class="app">
    <Navbar />
    <div class="upper">
      <SongMenu />
      <SongPanel />
    </div>
    <div class="lower">
      <Track />
    </div>
  </div>
</template>

<style scoped>
.join-gate {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.join-gate form {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  align-items: center;
}
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.upper {
  flex: 1 1 50%;
  display: grid;
  grid-template-columns: 320px 1fr;
  overflow: hidden;
  border-bottom: 1px solid #333;
}
.lower {
  flex: 1 1 50%;
  overflow: hidden;
}
</style>
