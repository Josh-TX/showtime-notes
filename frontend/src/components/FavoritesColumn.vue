<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api'
import { addNoteDropHandler, beginNoteDrag, noteDrag } from '../store/noteDrag'
import NoteChip from './NoteChip.vue'
import NoteContextMenu from './NoteContextMenu.vue'
import type { FavoriteNote } from '../types'

// One scrollable column of favorites: a drop target (insert at the pointer) and a drag source (reorder, or onto
// the timeline). Favorites are shared by all clients and live in server state.
const props = defineProps<{ title: string; column: number; notes: FavoriteNote[] }>()

const scroller = ref<HTMLElement | null>(null)
const chipEls = ref<HTMLElement[]>([])
const menu = ref<{ noteId: string; x: number; y: number } | null>(null)

// Insertion index (into props.notes) if dropped at the pointer, or null when the pointer is outside this column.
const hoverIndex = computed<number | null>(() => {
  if (!noteDrag.active) return null
  const rect = scroller.value?.getBoundingClientRect()
  if (!rect) return null
  const { pointerX: x, pointerY: y } = noteDrag
  if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) return null
  const index = chipEls.value.slice(0, props.notes.length).findIndex((el) => {
    const r = el.getBoundingClientRect()
    return y < r.top + r.height / 2
  })
  return index === -1 ? props.notes.length : index
})

function onDrop(): boolean {
  const item = noteDrag.item
  const index = hoverIndex.value
  if (!item || index === null) return false
  if (item.favoriteId) {
    // the server inserts after removing the favorite from its old spot, so shift for a same-column move downward
    const from = props.notes.findIndex((n) => n.id === item.favoriteId)
    api.moveFavorite(item.favoriteId, props.column, from !== -1 && from < index ? index - 1 : index)
  } else {
    api.addFavorite({ column: props.column, index, text: item.text, color: item.color })
    item.onDropped?.()
  }
  return true
}

let removeDropHandler: (() => void) | undefined
onMounted(() => (removeDropHandler = addNoteDropHandler(onDrop)))
onBeforeUnmount(() => removeDropHandler?.())

function onPress(e: PointerEvent, note: FavoriteNote): void {
  beginNoteDrag(e, e.currentTarget as HTMLElement, {
    id: null,
    favoriteId: note.id,
    text: note.text,
    color: note.color,
    trash: { label: 'delete from favorites', run: () => api.deleteFavorite(note.id) },
  })
}

function isDragged(note: FavoriteNote): boolean {
  return noteDrag.active && noteDrag.item?.favoriteId === note.id
}
</script>

<template>
  <div class="favorites-column">
    <h4>{{ title }}</h4>
    <div ref="scroller" class="scroller" :class="{ hovered: hoverIndex !== null }">
      <template v-for="(note, i) in notes" :key="note.id">
        <div v-if="hoverIndex === i" class="insert-line" />
        <NoteChip
          :ref="(c) => (chipEls[i] = (c as any)?.$el)"
          class="fav"
          :text="note.text"
          :color="note.color"
          :source="isDragged(note)"
          @press="onPress($event, note)"
          @contextmenu.prevent="menu = { noteId: note.id, x: $event.clientX, y: $event.clientY }"
        />
      </template>
      <div v-if="hoverIndex === notes.length" class="insert-line" />
    </div>
    <NoteContextMenu v-if="menu" kind="favorite" v-bind="menu" @close="menu = null" />
  </div>
</template>

<style scoped>
.favorites-column {
  position: relative;
  min-width: 0;
  padding: 0.5rem 0.6rem;
}
.scroller {
  position: absolute;
  inset: 2rem 0.3rem 0.3rem 0.6rem;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.4rem;
  padding: 0.2rem;
  overflow-y: auto;
  border-radius: 4px;
}
.scroller.hovered {
  background: rgba(0, 229, 255, 0.05);
}
.fav {
  max-width: 100%;
  flex: none;
}
.insert-line {
  flex: none;
  align-self: stretch;
  height: 2px;
  margin: -0.2rem 0;
  background: rgba(0, 229, 255, 0.6);
}
h4 {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #999;
}
</style>
