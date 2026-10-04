<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { api } from '../api'
import { useShowStore } from '../store/show'
import { clearNoteEdit, noteEdit, type NotePlace } from '../store/noteEdit'
import ColorPicker from './ColorPicker.vue'
import type { NoteColor } from '../types'

const MAX_TEXT_LENGTH = 200
const SAVE_DEBOUNCE_MS = 500

// kind picks which collection the note lives in: a song's timeline notes, or the shared favorites.
// noteId null = a new note at `place`; it is only created on the server once it has text.
const props = defineProps<{ kind: 'timeline' | 'favorite'; noteId: string | null; place?: NotePlace; x: number; y: number }>()
const emit = defineEmits<{ close: [] }>()

const store = useShowStore()
const menu = ref<HTMLElement | null>(null)
const input = ref<HTMLInputElement | null>(null)
const isNew = props.noteId === null
// menu position, nudged after mount so the whole menu stays on screen
const pos = ref({ x: props.x, y: props.y })
const songId = store.selectedSong?.id
let id = props.noteId
let discarded = false
let timer: number | undefined
// server calls run one after another, so edits typed before a new note's create call returns still find its id
let pending: Promise<unknown> = Promise.resolve()

const existing = computed(() => {
  const notes = props.kind === 'timeline' ? store.selectedSong?.timelineNotes : store.show?.favorites.flat()
  return notes?.find((n) => n.id === props.noteId) ?? null
})
const text = ref(existing.value?.text ?? '')
const color = ref<NoteColor>(existing.value?.color ?? 'gray')

Object.assign(noteEdit, {
  kind: props.kind,
  noteId: props.noteId,
  isNew,
  text: text.value,
  color: color.value,
  place: props.place ?? null,
})

function enqueue(fn: () => Promise<unknown>): void {
  pending = pending.then(fn).catch(console.error)
}

// Saves the current text/color: creates the note if new (and non-empty), otherwise patches it.
function save(): void {
  if (discarded) return
  const value = text.value.trim()
  const col = color.value
  if (id === null) {
    if (!value) return
    const place = props.place
    if (!place) return
    enqueue(async () => {
      if (props.kind === 'favorite' && 'column' in place) {
        id = (await api.addFavorite({ ...place, text: value, color: col })).id
      } else if (songId && 'timeSeconds' in place) {
        id = (await api.addTimelineNote(songId, { ...place, text: value, color: col })).id
      }
      noteEdit.noteId = id
    })
    return
  }
  enqueue(async () => {
    const patch = { text: value, color: col }
    if (props.kind === 'favorite') await api.updateFavorite(id!, patch)
    else if (songId) await api.updateTimelineNote(songId, id!, patch)
  })
}

function onInput(): void {
  noteEdit.text = text.value
  clearTimeout(timer)
  timer = window.setTimeout(save, SAVE_DEBOUNCE_MS)
}

function setColor(c: NoteColor): void {
  color.value = c
  noteEdit.color = c
  clearTimeout(timer)
  save()
}

function close(): void {
  if (timer !== undefined) {
    clearTimeout(timer)
    timer = undefined
    save()
  }
  emit('close')
}

function remove(): void {
  discarded = true
  clearTimeout(timer)
  // queued so a create call still in flight finishes first; then delete whatever it made
  enqueue(async () => {
    if (id === null) return
    if (props.kind === 'favorite') await api.deleteFavorite(id)
    else if (songId) await api.deleteTimelineNote(songId, id)
  })
  emit('close')
}

function onOutsidePointerDown(e: PointerEvent): void {
  if (!menu.value?.contains(e.target as Node)) close()
}
function onKeyDown(e: KeyboardEvent): void {
  if (e.key === 'Escape') close()
}

onMounted(() => {
  window.addEventListener('pointerdown', onOutsidePointerDown, true)
  window.addEventListener('keydown', onKeyDown)
  nextTick(() => {
    input.value?.focus()
    const el = menu.value
    if (!el) return
    pos.value = {
      x: Math.max(0, Math.min(props.x, window.innerWidth - el.offsetWidth)),
      y: Math.max(0, Math.min(props.y, window.innerHeight - el.offsetHeight)),
    }
  })
})
onUnmounted(() => {
  window.removeEventListener('pointerdown', onOutsidePointerDown, true)
  window.removeEventListener('keydown', onKeyDown)
  clearNoteEdit()
})
</script>

<template>
  <div v-if="isNew || existing" ref="menu" class="note-menu" :style="{ left: `${pos.x}px`, top: `${pos.y}px` }" @contextmenu.prevent>
    <input
      ref="input"
      v-model="text"
      placeholder="Note text"
      :maxlength="MAX_TEXT_LENGTH"
      @input="onInput"
      @keydown.enter="close"
    />
    <ColorPicker :model-value="color" @update:model-value="setColor" />
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
