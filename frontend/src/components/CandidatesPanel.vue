<script setup lang="ts">
import { useShowStore } from '../store/show'

// Rank order (best candidate first) maps to these colors; shared with Timeline.vue's bar coloring.
const CANDIDATE_COLORS = ['#00e5ff', '#ff00ff', '#ff9800']

const store = useShowStore()
</script>

<template>
  <div v-if="store.syncPhase === 'acquiring' && store.bestCandidates.length" class="candidates-panel">
    <div class="title">acquisition candidates</div>
    <div v-for="(candidate, rank) in store.bestCandidates" :key="candidate.barIndex" class="candidate-row">
      <span class="swatch" :style="{ background: CANDIDATE_COLORS[rank] }"></span>
      <span>score {{ candidate.score.toFixed(2) }}</span>
      <span>L {{ candidate.leftMargin.toFixed(2) }}</span>
      <span>R {{ candidate.rightMargin.toFixed(2) }}</span>
    </div>
  </div>
</template>

<style scoped>
.candidates-panel {
  position: fixed;
  right: 0.6rem;
  bottom: 0.6rem;
  z-index: 100;
  background: rgba(20, 20, 20, 0.9);
  border: 1px solid #444;
  border-radius: 4px;
  padding: 0.4rem 0.6rem;
  font-size: 0.75rem;
  color: #ddd;
  pointer-events: none;
}
.title {
  opacity: 0.7;
  margin-bottom: 0.3rem;
}
.candidate-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  white-space: nowrap;
}
.swatch {
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 50%;
  flex: none;
}
</style>
