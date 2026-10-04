<script setup lang="ts">
import { ref } from 'vue'
import SyncIndicator from './SyncIndicator.vue'
import ListenerIndicator from './ListenerIndicator.vue'
import NewRecordingModal from './NewRecordingModal.vue'
import SettingsModal from './SettingsModal.vue'

const settings = ref<InstanceType<typeof SettingsModal> | null>(null)
</script>

<template>
  <header class="navbar">
    <span class="brand">Showtime Notes</span>
    <SyncIndicator />
    <NewRecordingModal />
    <ListenerIndicator
      class="right"
      @click="settings?.openModal('listener')"
      @keydown.enter="settings?.openModal('listener')"
    />
    <SettingsModal ref="settings" />
  </header>
</template>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.4rem 1rem;
  background: #1a1a1a;
  border-bottom: 1px solid #333;
  height: 2.2rem;
}
.brand {
  font-weight: 700;
}
.right {
  margin-left: auto;
}
</style>
