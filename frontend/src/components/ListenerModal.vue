<script setup lang="ts">
import { computed, ref } from 'vue'
import { useShowStore } from '../store/show'
import { startCapture, startTabCapture, stopCapture } from '../audio/capture'
import { startPlayback, stopPlayback, pushPlaybackChunk } from '../audio/playback'
import { ws } from '../ws'

const store = useShowStore()
const dialog = ref<HTMLDialogElement | null>(null)
const showDevicePicker = ref(false)
const devices = ref<MediaDeviceInfo[]>([])
const selectedDeviceId = ref('')
const deviceError = ref(false)
const tabCaptureError = ref<string | null>(null)
const showModeChoice = ref(false)

const listenerLabel = computed(() =>
  store.show?.listener.deviceName ? `${store.show.listener.deviceName} is the listener` : 'server has no listener',
)
const becomeListenerLabel = computed(() =>
  store.show?.listener.deviceName ? 'Take over being the listener' : 'Become the listener',
)

function openModal(): void {
  dialog.value?.showModal()
}
function closeModal(): void {
  dialog.value?.close()
}
function onDialogClose(): void {
  showModeChoice.value = false
  showDevicePicker.value = false
  tabCaptureError.value = null
  if (store.wantsLiveAudio) stopLiveAudio()
}

async function onUseMicrophoneClick(): Promise<void> {
  showModeChoice.value = false
  showDevicePicker.value = true
  deviceError.value = false
  tabCaptureError.value = null
  try {
    const tempStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    tempStream.getTracks().forEach((track) => track.stop())
    const list = await navigator.mediaDevices.enumerateDevices()
    devices.value = list.filter((d) => d.kind === 'audioinput')
    selectedDeviceId.value = devices.value[0]?.deviceId ?? ''
  } catch {
    deviceError.value = true
    devices.value = []
  }
}
function cancelDevicePicker(): void {
  showDevicePicker.value = false
}
async function confirmBecomeListener(): Promise<void> {
  await startCapture(deviceError.value ? undefined : selectedDeviceId.value)
  store.becomeListener()
  showDevicePicker.value = false
}
function stopBeingListener(): void {
  stopCapture()
  store.releaseListener()
}

async function onShareTabClick(): Promise<void> {
  tabCaptureError.value = null
  try {
    await startTabCapture()
    store.becomeListener()
  } catch (err) {
    tabCaptureError.value = err instanceof Error ? err.message : 'Could not capture tab audio.'
  }
}

function stopLiveAudio(): void {
  store.setLiveAudioSubscription(false)
  stopPlayback()
  ws.offBinary(pushPlaybackChunk)
}

async function toggleLiveAudio(): Promise<void> {
  if (store.wantsLiveAudio) {
    stopLiveAudio()
  } else {
    await startPlayback()
    ws.onBinary(pushPlaybackChunk)
    store.setLiveAudioSubscription(true)
  }
}
</script>

<template>
  <div class="listener-root">
    <div class="listener-section" role="button" tabindex="0" @click="openModal" @keydown.enter="openModal">
      <div class="listener-label">{{ listenerLabel }}</div>
      <div class="loudness-meter" title="Live loudness">
        <div class="loudness-fill" :style="{ width: `${Math.round(store.loudness * 100)}%` }" />
      </div>
    </div>

    <dialog ref="dialog" class="listener-modal" @click.self="closeModal" @close="onDialogClose">
      <div class="modal-content">
        <h2>Listener</h2>
        <p class="explain">
          The listener streams audio to the server in real time. There are no other privledges to being the listener. Any client can start/stop recordings. 
        </p>
        <p class="explain">
          The server can only have 1 listener at a time
        </p>

        <div class="status-row">
          <p class="listener-status">{{ listenerLabel }}</p>
          <button v-if="!store.isListener && !showModeChoice && !showDevicePicker" @click="showModeChoice = true">
            {{ becomeListenerLabel }}
          </button>
          <button v-if="store.isListener" @click="stopBeingListener">Stop being the listener</button>
        </div>

        <div class="listener-flow">
          <template v-if="!store.isListener">
            <div v-if="showModeChoice && !showDevicePicker" class="card become-listener-actions">
              <div class="card-header-row">
                <div class="device-picker-header">Choose an audio source</div>
                <button class="text-button" @click="showModeChoice = false">Cancel</button>
              </div>
              <button @click="onUseMicrophoneClick">Use a microphone</button>
              <button @click="onShareTabClick">Share a browser tab</button>
            </div>

            <div v-if="showDevicePicker" class="card device-picker">
              <div class="card-header-row">
                <div class="device-picker-header">Choose a microphone</div>
                <button class="text-button" @click="cancelDevicePicker">Cancel</button>
              </div>
              <select v-if="!deviceError" v-model="selectedDeviceId">
                <option v-for="d in devices" :key="d.deviceId" :value="d.deviceId">
                  {{ d.label || 'Microphone' }}
                </option>
              </select>
              <p v-else class="device-error">Couldn't list microphones. Will use the default device.</p>
              <div class="device-picker-actions">
                <button @click="confirmBecomeListener">Start</button>
              </div>
            </div>
            <p v-if="tabCaptureError" class="device-error">{{ tabCaptureError }}</p>
          </template>
        </div>

        <div class="big-loudness-meter" title="Live loudness">
          <div class="big-loudness-fill" :style="{ width: `${Math.round(store.loudness * 100)}%` }" />
        </div>
        <div class="loudness-scale">
          <span>-70 dB</span>
          <span>-40 dB</span>
          <span>-10 dB</span>
        </div>

        <div class="modal-footer">
          <button :disabled="!store.show?.listener.deviceName" @click="toggleLiveAudio">
            {{ store.wantsLiveAudio ? 'Stop Testing Listener Audio' : 'Test Listener Audio' }}
          </button>
          <button @click="closeModal">Close</button>
        </div>
      </div>
    </dialog>
  </div>
</template>

<style scoped>
.listener-root {
  display: flex;
}
.listener-section {
  display: flex;
  flex-direction: column;
  width: 220px;
  padding: 0.15rem 0.6rem;
  cursor: pointer;
}
.listener-section:hover {
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

.listener-modal {
  border: none;
  border-radius: 8px;
  padding: 0;
  background: transparent;
  max-width: 480px;
  width: 90vw;
}
.listener-modal::backdrop {
  background: rgba(0, 0, 0, 0.6);
}
.modal-content {
  background: #1e1e1e;
  color: inherit;
  padding: 1.25rem;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.modal-content h2 {
  margin: 0;
}
.explain {
  color: #ccc;
  font-size: 0.9rem;
  margin: 0;
}
.big-loudness-meter {
  width: 100%;
  height: 8px;
  background: #333;
  border-radius: 4px;
  overflow: hidden;
}
.big-loudness-fill {
  height: 100%;
  background: #3ecf5f;
}
.loudness-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #888;
  margin-top: -5px;
}
.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}
.listener-status {
  margin: 0;
  font-weight: 600;
}
.listener-flow {
  min-height: 90px;
}
.card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.6rem;
  background: #262626;
}
.device-picker-header {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: #999;
}
.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.text-button {
  background: none;
  border: none;
  color: #8ab4f8;
  padding: 0;
  font-size: 0.75rem;
  cursor: pointer;
}
.device-picker-actions {
  display: flex;
  justify-content: flex-end;
}
.device-error {
  color: #e0a03e;
  font-size: 0.85rem;
  margin: 0;
}
.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
