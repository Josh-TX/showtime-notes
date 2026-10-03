<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { addNoteDropHandler, noteDrag } from '../store/noteDrag'

// Drop target that deletes the dragged note's source. Only shown while dragging something deletable.
const el = ref<HTMLElement | null>(null)
const visible = computed(() => noteDrag.active && !!noteDrag.item?.trash)

// Fixed + teleported to body so it paints above the toolbar (a sibling stacking context). Anchored to the
// bottom-left of the parent panel, straddling its bottom edge; measured when a drag starts (layout is static then).
const anchor = ref({ left: 0, top: 0 })
const placeholder = ref<HTMLElement | null>(null)
watch(visible, (v) => {
  const r = placeholder.value?.parentElement?.getBoundingClientRect()
  if (v && r) anchor.value = { left: r.left, top: r.bottom }
})

function pointerOver(): boolean {
  const r = el.value?.getBoundingClientRect()
  if (!r) return false
  const radius = r.width / 2
  return Math.hypot(noteDrag.pointerX - (r.left + radius), noteDrag.pointerY - (r.top + radius)) <= radius
}

const hovered = computed(() => visible.value && pointerOver())

function onDrop(): boolean {
  if (!visible.value || !pointerOver()) return false
  noteDrag.item?.trash?.run()
  return true
}

let removeDropHandler: (() => void) | undefined
onMounted(() => (removeDropHandler = addNoteDropHandler(onDrop)))
onBeforeUnmount(() => removeDropHandler?.())
</script>

<template>
  <span ref="placeholder" hidden />
  <Teleport to="body">
    <div
      v-show="visible"
      ref="el"
      class="trash"
      :class="{ hovered }"
      :style="{ left: `${anchor.left}px`, top: `${anchor.top}px` }"
    >
      <span class="text idle">trash</span>
      <span class="text action">{{ noteDrag.item?.trash?.label }}</span>
    </div>
  </Teleport>
</template>

<style scoped>
.trash {
  position: fixed;
  margin: -3.5rem 0 0 0.6rem; /* straddles the panel's bottom edge, mostly over the toolbar below */
  width: 6rem;
  height: 6rem;
  box-sizing: border-box;
  display: grid;
  place-items: center;
  padding: 0 0.8rem;
  color: #bbb;
  font-size: 0.9rem;
  text-transform: uppercase;
  text-align: center;
  pointer-events: none;
  z-index: 3; /* above the toolbar, below timeline notes (z-index 4) and the drag ghost */
}
/* the circle scales on hover; the text stays the same size */
.trash::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: 50%;
  background: rgba(0, 0, 1, 0.6);
  box-shadow: 0 3px 5px rgba(0, 0, 0, 0.4);
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}
/* both texts share one grid cell and cross-fade */
.text {
  grid-area: 1 / 1;
  transition: opacity 0.2s;
}
.action,
.trash.hovered .idle {
  opacity: 0;
}
.trash.hovered .action {
  opacity: 1;
  color: #fff;
}
.trash.hovered::before {
  transform: scale(1.4);
  box-shadow: 0 5px 8px rgba(0, 0, 0, 0.45);
}
</style>
