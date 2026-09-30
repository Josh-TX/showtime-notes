import type { NoteColor } from '../types'

export const NOTE_COLORS: Record<NoteColor, string> = {
  red: '#e05050',
  blue: '#4a8cf0',
  orange: '#f08a2c',
  yellow: '#e8d23a',
  green: '#3ecf5f',
  pink: '#f078b8',
  brown: '#9a6a3c',
  white: '#f2f2f2',
  gray: '#8a8a8a',
  purple: '#a060e0',
}

export const NOTE_COLOR_NAMES = Object.keys(NOTE_COLORS) as NoteColor[]
