<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useShowStore } from '../store/show'
import { clientSettings } from '../store/clientSettings'
import { beginNoteDrag, noteDrag } from '../store/noteDrag'
import ColorPicker from './ColorPicker.vue'
import FavoritesColumn from './FavoritesColumn.vue'
import NoteChip from './NoteChip.vue'
import TrashBubble from './TrashBubble.vue'

const MAX_TEXT_LENGTH = 200

const store = useShowStore()

const newText = ref('')
const trimmedText = computed(() => newText.value.trim())
const draftPressed = ref(false)
const draftIsSource = computed(() => draftPressed.value && noteDrag.active)
watch(
  () => noteDrag.item,
  (item) => {
    if (!item) draftPressed.value = false
  },
)

function onPress(e: PointerEvent): void {
  if (!trimmedText.value) return
  draftPressed.value = true
  const noteEl = e.currentTarget as HTMLElement
  beginNoteDrag(e, noteEl, {
    id: null,
    text: trimmedText.value,
    color: clientSettings.lastNoteColor,
    onDropped: () => (newText.value = ''),
    trash: { label: 'delete new note', run: () => (newText.value = '') },
  })
}
</script>

<template>
  <div class="timeline-notes-panel">
    <div class="card">
      <div class="card-body">
        <div class="section divided">
          <h4>New timeline note</h4>
          <input v-model="newText" placeholder="Note text" :maxlength="MAX_TEXT_LENGTH" />
          <ColorPicker v-model="clientSettings.lastNoteColor" />
          <NoteChip
            v-if="newText !== ''"
            class="draft"
            :text="trimmedText"
            :color="clientSettings.lastNoteColor"
            :source="draftIsSource"
            @press="onPress"
          />
          <div v-else class="placeholder">type text, then drag onto the timeline</div>
        </div>
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
  grid-template-columns: repeat(4, minmax(0, 1fr));
  flex: 1;
  min-height: 12rem;
}
.section {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.4rem;
  padding: 0.5rem 0.6rem;
  min-width: 0;
}
.section.divided {
  border-right: 1px solid #333;
}
.favorites-divider {
  border-right: 1px solid #333;
}
.section input {
  align-self: stretch;
}
h4 {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #999;
}
input {
  padding: 0.25rem 0.5rem;
  background: #1c1c1c;
}
.placeholder {
  box-sizing: border-box;
  height: 32px;
  max-width: 100%;
  padding: 0 8px;
  display: flex;
  align-items: center;
  border: 1px dashed #555;
  font-size: 0.8rem;
  color: #777;
  white-space: nowrap;
}
.draft {
  max-width: 100%;
}
</style>
