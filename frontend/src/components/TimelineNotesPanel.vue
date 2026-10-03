<script setup lang="ts">
import { useShowStore } from '../store/show'
import FavoritesColumn from './FavoritesColumn.vue'
import TrashBubble from './TrashBubble.vue'

const store = useShowStore()
</script>

<template>
  <div class="timeline-notes-panel">
    <div class="card">
      <div class="card-body">
        <FavoritesColumn class="favorites-divider" title="Favorites 1" :column="0" :notes="store.show?.favorites[0] ?? []" />
        <FavoritesColumn class="favorites-divider" title="Favorites 2" :column="1" :notes="store.show?.favorites[1] ?? []" />
        <FavoritesColumn title="Favorites 3" :column="2" :notes="store.show?.favorites[2] ?? []" />
      </div>
    </div>
    <TrashBubble />
  </div>
</template>

<style scoped>
.timeline-notes-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}
.card {
  flex: 1;
  min-height: 0;
  display: flex;
  border: 1px solid #333;
  border-radius: 6px;
  background: #16161a;
}
.card-body {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  flex: 1;
  min-height: 12rem;
}
.favorites-divider {
  border-right: 1px solid #333;
}
</style>
