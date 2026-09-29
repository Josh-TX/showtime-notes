<script setup lang="ts">
import SyncIndicator from './SyncIndicator.vue'
import ListenerModal from './ListenerModal.vue'
import SettingsModal from './SettingsModal.vue'
</script>

<template>
  <header class="navbar">
    <span class="brand">Showtime Notes</span>
    <SyncIndicator />
    <ListenerModal class="right" />
    <SettingsModal />
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
