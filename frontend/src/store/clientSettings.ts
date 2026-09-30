import { reactive, watch } from 'vue'
import { NOTE_COLORS } from './noteColors'
import type { NoteColor } from '../types'

const STORAGE_KEY = 'showtimeNotes'

export interface ClientSettings {
  deviceName: string
  timelineWidthSeconds: number
  autoScrollLeftOffsetPercent: number
  lastNoteColor: NoteColor
}

export const SETTING_LIMITS = {
  timelineWidthSeconds: { min: 5, max: 300 },
  autoScrollLeftOffsetPercent: { min: 0, max: 100 },
}

const defaults: ClientSettings = {
  deviceName: '',
  timelineWidthSeconds: 30,
  autoScrollLeftOffsetPercent: 25,
  lastNoteColor: 'gray',
}

function clamp(value: unknown, min: number, max: number, fallback: number): number {
  const n = Number(value)
  if (!Number.isFinite(n)) return fallback
  return Math.min(max, Math.max(min, n))
}

function load(): ClientSettings {
  let raw: Partial<ClientSettings> = {}
  try {
    raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') ?? {}
  } catch {
    // corrupt entry, use defaults
  }
  const w = SETTING_LIMITS.timelineWidthSeconds
  const o = SETTING_LIMITS.autoScrollLeftOffsetPercent
  return {
    deviceName: typeof raw.deviceName === 'string' ? raw.deviceName : defaults.deviceName,
    timelineWidthSeconds: clamp(raw.timelineWidthSeconds, w.min, w.max, defaults.timelineWidthSeconds),
    autoScrollLeftOffsetPercent: clamp(raw.autoScrollLeftOffsetPercent, o.min, o.max, defaults.autoScrollLeftOffsetPercent),
    lastNoteColor: raw.lastNoteColor && raw.lastNoteColor in NOTE_COLORS ? raw.lastNoteColor : defaults.lastNoteColor,
  }
}

export const clientSettings = reactive<ClientSettings>(load())

watch(clientSettings, (s) => localStorage.setItem(STORAGE_KEY, JSON.stringify(s)), { deep: true })

export function setTimelineWidthSeconds(value: unknown): void {
  const l = SETTING_LIMITS.timelineWidthSeconds
  clientSettings.timelineWidthSeconds = clamp(value, l.min, l.max, clientSettings.timelineWidthSeconds)
}

export function setAutoScrollLeftOffsetPercent(value: unknown): void {
  const l = SETTING_LIMITS.autoScrollLeftOffsetPercent
  clientSettings.autoScrollLeftOffsetPercent = clamp(value, l.min, l.max, clientSettings.autoScrollLeftOffsetPercent)
}

export function setDeviceName(value: string): void {
  const name = value.trim()
  if (name) clientSettings.deviceName = name
}
