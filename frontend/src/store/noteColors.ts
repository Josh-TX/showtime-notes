import type { NoteColor } from '../types'

// Picker order: 3 rows (light, saturated, dark) of 8 columns: white/gray/black, then rainbow.
const PICKER_COLORS = {
  white: '#f2f2f2',
  'light-red': '#f5a3a3',
  'light-orange': '#f8b08f',
  'light-yellow': '#f5e98f',
  'light-green': '#9fe5ae',
  'light-blue': '#a3d4f8',
  'light-purple': '#c4aaf2',
  'light-pink': '#f8b8dc',
  gray: '#8a8a8a',
  red: '#e05050',
  orange: '#f08a2c',
  yellow: '#e8d23a',
  green: '#3ecf5f',
  blue: '#4a8cf0',
  purple: '#a060e0',
  pink: '#f078b8',
  black: '#262626',
  'dark-red': '#5c1414',
  'dark-orange': '#5e3a14',
  'dark-yellow': '#5e5410',
  'dark-green': '#215a1c',
  'dark-blue': '#14285c',
  'dark-purple': '#3d1f66',
  'dark-pink': '#66284a',
} as const

// No longer in the picker, but may still be on saved notes.
const LEGACY_COLORS = {
  'light-gray': '#cfcfcf',
  'dark-gray': '#555555',
  silver: '#a8a8a8',
  brown: '#9a6a3c',
} as const

export const NOTE_COLORS: Record<NoteColor, string> = { ...PICKER_COLORS, ...LEGACY_COLORS }

export const NOTE_COLOR_NAMES = Object.keys(PICKER_COLORS) as NoteColor[]
