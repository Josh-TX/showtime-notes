<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useShowStore } from '../store/show'
import { captureState, getCaptureDeviceId, startCapture, startTabCapture, stopCapture } from '../audio/capture'
import { startPlayback, stopPlayback, pushPlaybackChunk } from '../audio/playback'
import { ws } from '../ws'
import { clientSettings } from '../store/clientSettings'

const store = useShowStore()
const devices = ref<MediaDeviceInfo[]>([])
const selectedDeviceId = ref('')
const captureError = ref<string | null>(null)
const showModeChoice = ref(false)
const isSecureContext = window.isSecureContext

const listenerLabel = computed(() =>
  store.show?.listener.deviceName ? `${store.show.listener.deviceName} is the listener` : 'server has no listener',
)
const hasListener = computed(() => !!store.show?.listener.deviceName)
const modeChoiceVisible = computed(
  () => !store.isListener && (showModeChoice.value || !hasListener.value),
)
const becomeListenerLabel = computed(() =>
  store.show?.listener.deviceName ? 'Take over being the listener' : 'Become the listener',
)

watch(
  () => store.isListener,
  (isListener) => {
    if (isListener && store.wantsLiveAudio) stopLiveAudio()
  },
)

onMounted(() => {
  if (captureState.kind === 'mic') refreshDevices()
})

onBeforeUnmount(() => {
  if (store.wantsLiveAudio) stopLiveAudio()
})

async function onUseMicrophoneClick(): Promise<void> {
  captureError.value = null
  try {
    await startCapture()
  } catch (err) {
    captureError.value = err instanceof Error ? err.message : 'Could not access the microphone.'
    return
  }
  showModeChoice.value = false
  store.becomeListener()
  await refreshDevices()
}
async function refreshDevices(): Promise<void> {
  selectedDeviceId.value = getCaptureDeviceId() ?? ''
  const list = await navigator.mediaDevices.enumerateDevices()
  devices.value = list.filter((d) => d.kind === 'audioinput')
}
async function selectDevice(deviceId: string): Promise<void> {
  if (deviceId === selectedDeviceId.value) return
  captureError.value = null
  stopCapture()
  try {
    await startCapture(deviceId)
    selectedDeviceId.value = deviceId
  } catch (err) {
    captureError.value = err instanceof Error ? err.message : 'Could not switch microphone.'
    stopBeingListener()
  }
}
function stopBeingListener(): void {
  stopCapture()
  store.releaseListener()
}

async function onShareTabClick(): Promise<void> {
  captureError.value = null
  try {
    await startTabCapture()
    showModeChoice.value = false
    store.becomeListener()
  } catch (err) {
    captureError.value = err instanceof Error ? err.message : 'Could not capture tab audio.'
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
  <div class="listener-section">
        <h2>Listener</h2>
        <div class="checkbox-setting">
          <label class="checkbox-row">
            <input v-model="clientSettings.autoBecomeListener" type="checkbox" />
            Auto-open listener settings on page load
          </label>
        </div>
        <p class="explain">
          The listener streams audio to the server in real time. There are no other privledges to being the listener. Any client can start/stop recordings. 
        </p>
        <p class="explain">
          The server can only have 1 listener at a time
        </p>

        <div class="status-row">
          <p class="listener-status">{{ listenerLabel }}</p>
          <button v-if="!store.isListener && !modeChoiceVisible" @click="showModeChoice = true">
            {{ becomeListenerLabel }}
          </button>
          <button v-if="store.isListener" @click="stopBeingListener">Stop being the listener</button>
        </div>

        <div class="card listener-card">
          <template v-if="modeChoiceVisible">
            <div class="card-header-row">
              <div class="device-picker-header">Choose an audio source</div>
              <button v-if="hasListener" class="text-button" @click="showModeChoice = false">Cancel</button>
            </div>
            <p v-if="!isSecureContext" class="device-error">
              Not a secure context (needs https or localhost). The browser will likely block audio capture.
            </p>
            <div class="source-buttons">
              <button class="source-button" :disabled="!isSecureContext" @click="onUseMicrophoneClick">
                <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <rect x="9" y="3" width="6" height="11" rx="3" />
                  <path d="M5.5 11a6.5 6.5 0 0 0 13 0" />
                  <path d="M12 17.5V21" />
                  <path d="M8.5 21h7" />
                </svg>
                Microphone
              </button>
              <button class="source-button" :disabled="!isSecureContext" @click="onShareTabClick">
                <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <rect x="3" y="4" width="18" height="12" rx="2" />
                  <path d="M8 20h8" />
                  <path d="M12 16v4" />
                </svg>
                Browser Tab
              </button>
            </div>
            <p v-if="captureError" class="device-error">{{ captureError }}</p>
          </template>
          <template v-else-if="store.isListener && captureState.kind === 'mic'">
            <div class="device-picker-header">Microphone</div>
            <div class="device-list" role="listbox">
              <button
                v-for="d in devices"
                :key="d.deviceId"
                class="device-option"
                :class="{ selected: d.deviceId === selectedDeviceId }"
                role="option"
                :aria-selected="d.deviceId === selectedDeviceId"
                @click="selectDevice(d.deviceId)"
              >
                {{ d.label || 'Microphone' }}
              </button>
            </div>
          </template>
          <template v-else-if="store.isListener && captureState.kind === 'tab'">
            <div class="device-picker-header">Browser tab</div>
            <p class="card-message">Streaming audio from the shared browser tab.</p>
          </template>
          <template v-else-if="!store.isListener">
            <div class="device-picker-header">Audio source</div>
            <p class="card-message">Another device is the listener.</p>
            <button class="test-button" @click="toggleLiveAudio">
              {{ store.wantsLiveAudio ? 'Stop Testing Listener Audio' : 'Test Listener Audio' }}
            </button>
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
  </div>
</template>

<style scoped>
.listener-section {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.listener-section h2 {
  margin: 0;
}
.explain {
  color: #ccc;
  font-size: 0.9rem;
  margin: 0;
}
.checkbox-setting {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.checkbox-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: #ccc;
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
.source-buttons {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 0.6rem;
}
.source-button {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  padding: 0.25rem 0.5rem;
  font-size: 1rem;
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
.listener-card {
  height: 150px;
  box-sizing: border-box;
  overflow-y: auto;
}
.test-button {
  align-self: flex-start;
}
.card-message {
  margin: 0;
  color: #999;
  font-size: 0.85rem;
}
.device-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.device-option {
  text-align: left;
  background: transparent;
  border: none;
  border-left: 2px solid transparent;
  border-radius: 0;
  color: #bbb;
  padding: 0.2rem 0.6rem;
  font-size: 0.85rem;
  cursor: pointer;
  flex-shrink: 0;
}
.device-option:hover {
  background: #2c2c2c;
}
.device-option.selected {
  border-left-color: #22d3ee;
  background: rgba(34, 211, 238, 0.1);
  color: #fff;
}
.device-error {
  color: #e0a03e;
  font-size: 0.85rem;
  margin: 0;
}
</style>
