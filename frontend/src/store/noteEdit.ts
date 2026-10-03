import { reactive } from 'vue'
import type { NoteColor } from '../types'

// The note being edited in the context menu. Chips for that note render this text/color instead of the saved
// ones, so typing updates them immediately. A new note has noteId null until its first save; place says where
// its draft chip goes.
export type NotePlace = { timeSeconds: number; y: number } | { column: number; index: number }

export const noteEdit = reactive({
  kind: null as 'timeline' | 'favorite' | null,
  noteId: null as string | null,
  isNew: false,
  text: '',
  color: 'gray' as NoteColor,
  place: null as NotePlace | null,
})

export function clearNoteEdit(): void {
  noteEdit.kind = null
  noteEdit.noteId = null
  noteEdit.isNew = false
  noteEdit.place = null
}
