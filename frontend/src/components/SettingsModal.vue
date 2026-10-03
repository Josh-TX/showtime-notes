<script setup lang="ts">
import { ref } from 'vue'
import {
  clientSettings,
  SETTING_LIMITS,
  setAutoScrollLeftOffsetPercent,
  setDeviceName,
  setTimelineWidthSeconds,
} from '../store/clientSettings'

type Section = 'client' | 'server'

const dialog = ref<HTMLDialogElement | null>(null)
const section = ref<Section>('client')

function openModal(): void {
  dialog.value?.showModal()
}
function closeModal(): void {
  dialog.value?.close()
}

function onDeviceName(e: Event): void {
  const input = e.target as HTMLInputElement
  setDeviceName(input.value)
  input.value = clientSettings.deviceName
}
function onTimelineWidth(e: Event): void {
  const input = e.target as HTMLInputElement
  setTimelineWidthSeconds(input.value)
  input.value = String(clientSettings.timelineWidthSeconds)
}
function onOffset(e: Event): void {
  const input = e.target as HTMLInputElement
  setAutoScrollLeftOffsetPercent(input.value)
  input.value = String(clientSettings.autoScrollLeftOffsetPercent)
}
</script>

<template>
  <div>
    <button @click="openModal">Settings</button>

    <dialog ref="dialog" class="settings-modal" @click.self="closeModal">
      <div class="modal-content">
        <div class="body">
          <nav class="sidebar">
            <button :class="{ active: section === 'client' }" @click="section = 'client'">Client Settings</button>
            <button :class="{ active: section === 'server' }" @click="section = 'server'">Server Settings</button>
          </nav>
          <div class="section">
            <template v-if="section === 'client'">
              <h2>Client Settings</h2>
              <label>
                Device name
                <input type="text" :value="clientSettings.deviceName" @change="onDeviceName" />
              </label>
              <label>
                Timeline width (seconds)
                <input
                  type="number"
                  :min="SETTING_LIMITS.timelineWidthSeconds.min"
                  :max="SETTING_LIMITS.timelineWidthSeconds.max"
                  step="0.01"
                  :value="clientSettings.timelineWidthSeconds"
                  @change="onTimelineWidth"
                />
              </label>
              <label>
                Auto-Scroll left offset (%)
                <input
                  type="number"
                  :min="SETTING_LIMITS.autoScrollLeftOffsetPercent.min"
                  :max="SETTING_LIMITS.autoScrollLeftOffsetPercent.max"
                  :value="clientSettings.autoScrollLeftOffsetPercent"
                  @change="onOffset"
                />
              </label>
            </template>
            <template v-else>
              <h2>Server Settings</h2>
              <p class="empty">no settings implemented yet</p>
            </template>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="closeModal">Close</button>
        </div>
      </div>
    </dialog>
  </div>
</template>

<style scoped>
.settings-modal {
  border: none;
  border-radius: 8px;
  padding: 0;
  background: transparent;
  max-width: 640px;
  width: 90vw;
}
.settings-modal::backdrop {
  background: rgba(0, 0, 0, 0.6);
}
.modal-content {
  background: #1e1e1e;
  color: inherit;
  padding: 1.25rem;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.body {
  display: flex;
  gap: 1rem;
  min-height: 240px;
}
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  width: 160px;
  border-right: 1px solid #333;
  padding-right: 1rem;
}
.sidebar button {
  text-align: left;
  background: none;
  border: none;
  color: #ccc;
  padding: 0.4rem 0.6rem;
  cursor: pointer;
  border-radius: 4px;
}
.sidebar button:hover {
  background: #262626;
}
.sidebar button.active {
  background: #333;
  color: #fff;
}
.section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.section h2 {
  margin: 0;
}
.section label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.85rem;
  color: #ccc;
}
.empty {
  color: #888;
  margin: 0;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
}
</style>
