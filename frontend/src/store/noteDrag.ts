import { reactive } from 'vue'
import type { NoteColor } from '../types'

// Shared drag-a-note state. Any note-shaped element (a timeline note, the "new note" draft, a favorite)
// starts a drag with beginNoteDrag. Drop targets (the timeline's notes layer, the favorites columns) read the
// state, show their own hover feedback, and register a drop handler.
export interface DragItem {
  id: string | null // existing timeline note being moved; null for anything else
  favoriteId?: string // set when the dragged note is an existing favorite
  text: string
  color: NoteColor
  onDropped?: () => void // called once the drop landed on a valid spot
  trash?: { label: string; run: () => void } // present when the source can be deleted by dropping on the trash bubble
}

// A press becomes a drag after moving this far, or after being held this long. The hold matters during
// auto-scroll, where the timeline moves under a mouse that never does.
const DRAG_START_DISTANCE_PX = 4
const DRAG_HOLD_MS = 200

export const noteDrag = reactive({
  item: null as DragItem | null,
  active: false,
  // the timeline layer reports whether the pointer is over a valid spot (it then shows its own snapped preview)
  valid: false,
  pointerX: 0,
  pointerY: 0,
  grabX: 0,
  grabY: 0,
})

// A handler returns true if the pointer was over its target and it consumed the drop.
const dropHandlers = new Set<() => boolean>()
let pressX = 0
let pressY = 0
let holdTimer: number | undefined

export function addNoteDropHandler(handler: () => boolean): () => void {
  dropHandlers.add(handler)
  return () => dropHandlers.delete(handler)
}

function activate(): void {
  if (!noteDrag.item) return
  noteDrag.active = true
  document.body.classList.add('note-dragging')
}

function onPointerMove(e: PointerEvent): void {
  noteDrag.pointerX = e.clientX
  noteDrag.pointerY = e.clientY
  if (!noteDrag.active && Math.hypot(e.clientX - pressX, e.clientY - pressY) >= DRAG_START_DISTANCE_PX) activate()
}

function onPointerUp(): void {
  if (noteDrag.active) for (const handler of dropHandlers) if (handler()) break
  endNoteDrag()
}

function onKeyDown(e: KeyboardEvent): void {
  if (e.key === 'Escape') endNoteDrag()
}

export function endNoteDrag(): void {
  window.clearTimeout(holdTimer)
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', endNoteDrag)
  window.removeEventListener('keydown', onKeyDown)
  noteDrag.item = null
  noteDrag.active = false
  noteDrag.valid = false
  document.body.classList.remove('note-dragging')
}

// Call from a note's pointerdown. noteEl is the element that visually is the note (grab offset origin).
export function beginNoteDrag(e: PointerEvent, noteEl: HTMLElement, item: DragItem): void {
  if (e.button !== 0) return
  endNoteDrag()
  const r = noteEl.getBoundingClientRect()
  noteDrag.item = item
  noteDrag.grabX = e.clientX - r.left
  noteDrag.grabY = e.clientY - r.top
  pressX = noteDrag.pointerX = e.clientX
  pressY = noteDrag.pointerY = e.clientY
  holdTimer = window.setTimeout(activate, DRAG_HOLD_MS)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', endNoteDrag)
  window.addEventListener('keydown', onKeyDown)
}
