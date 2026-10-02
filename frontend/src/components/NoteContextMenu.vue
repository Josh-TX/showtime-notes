<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'
import ColorPicker from './ColorPicker.vue'
import type { NoteColor } from '../types'

const MAX_TEXT_LENGTH = 200

// kind picks which collection noteId lives in: a song's timeline notes, or the shared favorites
const props = defineProps<{ kind: 'timeline' | 'favorite'; noteId: string; x: number; y: number }>()
const emit = defineEmits<{ close: [] }>()

const store = useShowStore()
const menu = ref<HTMLElement | null>(null)
const note = computed(() => {
  const notes = props.kind === 'timeline' ? store.selectedSong?.timelineNotes : store.show?.favorites.flat()
  return notes?.find((n) => n.id === props.noteId) ?? null
})
const text = ref(note.value?.text ?? '')

function patch(p: { text?: string; color?: NoteColor }): void {
  const song = store.selectedSong
  if (!note.value) return
  if (props.kind === 'favorite') api.updateFavorite(note.value.id, p)
  else if (song) api.updateTimelineNote(song.id, note.value.id, p)
}

// Empty text is not allowed; the old text is kept.
function commitText(): void {
  const trimmed = text.value.trim()
  if (trimmed && trimmed !== note.value?.text) patch({ text: trimmed })
}

function close(): void {
  commitText()
  emit('close')
}

async function remove(): Promise<void> {
  const song = store.selectedSong
  emit('close')
  if (props.kind === 'favorite') await api.deleteFavorite(props.noteId)
  else if (song) await api.deleteTimelineNote(song.id, props.noteId)
}

function onOutsidePointerDown(e: PointerEvent): void {
  if (!menu.value?.contains(e.target as Node)) close()
}
function onKeyDown(e: KeyboardEvent): void {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => {
  window.addEventListener('pointerdown', onOutsidePointerDown, true)
  window.addEventListener('keydown', onKeyDown)
})
onUnmounted(() => {
  window.removeEventListener('pointerdown', onOutsidePointerDown, true)
  window.removeEventListener('keydown', onKeyDown)
})
</script>

<template>
  <div v-if="note" ref="menu" class="note-menu" :style="{ left: `${x}px`, top: `${y}px` }" @contextmenu.prevent>
    <input
      v-model="text"
      placeholder="Note text"
      :maxlength="MAX_TEXT_LENGTH"
      autofocus
      @keydown.enter="close"
      @blur="commitText"
    />
    <ColorPicker :model-value="note.color" @update:model-value="patch({ color: $event })" />
    <button class="delete" @click="remove">Delete note</button>
  </div>
</template>

<style scoped>
.note-menu {
  position: fixed;
  pointer-events: auto;
  z-index: 100;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.6rem;
  background: #16161a;
  border: 1px solid #444;
  border-radius: 6px;
  box-shadow: 0 4px 16px #000;
}
input {
  align-self: stretch;
  padding: 0.25rem 0.5rem;
  background: #1c1c1c;
}
.delete {
  font-size: 0.8rem;
  padding: 0.1rem 0.6rem;
  color: #e05050;
  border-color: #5a2a2a;
}
</style>
