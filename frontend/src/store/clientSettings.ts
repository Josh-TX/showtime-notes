import { reactive, watch } from 'vue'
import { NOTE_COLORS } from './noteColors'
import type { NoteColor } from '../types'

const STORAGE_KEY = 'showtimeNotes'

export interface ClientSettings {
  deviceName: string
  timelineWidthSeconds: number
  autoScrollLeftOffsetPercent: number
  lastNoteColor: NoteColor
  autoBecomeListener: boolean
  autoSelectNextSeconds: number
}

export const SETTING_LIMITS = {
  timelineWidthSeconds: { min: 3, max: 300 },
  autoScrollLeftOffsetPercent: { min: 0, max: 100 },
  autoSelectNextSeconds: { min: 0, max: 60 },
}

const defaults: ClientSettings = {
  deviceName: '',
  timelineWidthSeconds: 30,
  autoScrollLeftOffsetPercent: 25,
  lastNoteColor: 'gray',
  autoBecomeListener: false,
  autoSelectNextSeconds: 3,
}

function round2(n: number): number {
  return Math.round(n * 100) / 100
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
  const a = SETTING_LIMITS.autoSelectNextSeconds
  const o = SETTING_LIMITS.autoScrollLeftOffsetPercent
  return {
    deviceName: typeof raw.deviceName === 'string' ? raw.deviceName : defaults.deviceName,
    timelineWidthSeconds: round2(clamp(raw.timelineWidthSeconds, w.min, w.max, defaults.timelineWidthSeconds)),
    autoScrollLeftOffsetPercent: clamp(raw.autoScrollLeftOffsetPercent, o.min, o.max, defaults.autoScrollLeftOffsetPercent),
    lastNoteColor: raw.lastNoteColor && raw.lastNoteColor in NOTE_COLORS ? raw.lastNoteColor : defaults.lastNoteColor,
    autoBecomeListener: typeof raw.autoBecomeListener === 'boolean' ? raw.autoBecomeListener : defaults.autoBecomeListener,
    autoSelectNextSeconds: clamp(raw.autoSelectNextSeconds, a.min, a.max, defaults.autoSelectNextSeconds),
  }
}

export const clientSettings = reactive<ClientSettings>(load())

watch(clientSettings, (s) => localStorage.setItem(STORAGE_KEY, JSON.stringify(s)), { deep: true })

export function setTimelineWidthSeconds(value: unknown): void {
  const l = SETTING_LIMITS.timelineWidthSeconds
  clientSettings.timelineWidthSeconds = round2(clamp(value, l.min, l.max, clientSettings.timelineWidthSeconds))
}

export function setAutoScrollLeftOffsetPercent(value: unknown): void {
  const l = SETTING_LIMITS.autoScrollLeftOffsetPercent
  clientSettings.autoScrollLeftOffsetPercent = clamp(value, l.min, l.max, clientSettings.autoScrollLeftOffsetPercent)
}

export function setDeviceName(value: string): void {
  const name = value.trim()
  if (name) clientSettings.deviceName = name
}

export function setAutoSelectNextSeconds(value: unknown): void {
  const l = SETTING_LIMITS.autoSelectNextSeconds
  clientSettings.autoSelectNextSeconds = round2(clamp(value, l.min, l.max, clientSettings.autoSelectNextSeconds))
}
