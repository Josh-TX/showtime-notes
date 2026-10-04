import { reactive, watch } from 'vue'

const STORAGE_KEY = 'showtimeNotes'

export interface ClientSettings {
  deviceName: string
  timelineWidthSeconds: number
  trackingScrollLeftOffsetPercent: number
  playbackScrollLeftOffsetPercent: number
  autoBecomeListener: boolean
  autoSelectNextSeconds: number
}

export const SETTING_LIMITS = {
  timelineWidthSeconds: { min: 3, max: 300 },
  scrollLeftOffsetPercent: { min: 0, max: 100 },
  autoSelectNextSeconds: { min: 0, max: 60 },
}

const defaults: ClientSettings = {
  deviceName: '',
  timelineWidthSeconds: 30,
  trackingScrollLeftOffsetPercent: 20,
  playbackScrollLeftOffsetPercent: 50,
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
  let raw: Partial<ClientSettings> & { autoScrollLeftOffsetPercent?: number } = {}
  try {
    raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') ?? {}
  } catch {
    // corrupt entry, use defaults
  }
  const w = SETTING_LIMITS.timelineWidthSeconds
  const a = SETTING_LIMITS.autoSelectNextSeconds
  const o = SETTING_LIMITS.scrollLeftOffsetPercent
  // legacy single setting seeds both new ones
  const legacy = raw.autoScrollLeftOffsetPercent
  return {
    deviceName: typeof raw.deviceName === 'string' ? raw.deviceName : defaults.deviceName,
    timelineWidthSeconds: round2(clamp(raw.timelineWidthSeconds, w.min, w.max, defaults.timelineWidthSeconds)),
    trackingScrollLeftOffsetPercent: round2(clamp(raw.trackingScrollLeftOffsetPercent ?? legacy, o.min, o.max, defaults.trackingScrollLeftOffsetPercent)),
    playbackScrollLeftOffsetPercent: round2(clamp(raw.playbackScrollLeftOffsetPercent ?? legacy, o.min, o.max, defaults.playbackScrollLeftOffsetPercent)),
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

export function setTrackingScrollLeftOffsetPercent(value: unknown): void {
  const l = SETTING_LIMITS.scrollLeftOffsetPercent
  clientSettings.trackingScrollLeftOffsetPercent = round2(clamp(value, l.min, l.max, clientSettings.trackingScrollLeftOffsetPercent))
}

export function setPlaybackScrollLeftOffsetPercent(value: unknown): void {
  const l = SETTING_LIMITS.scrollLeftOffsetPercent
  clientSettings.playbackScrollLeftOffsetPercent = round2(clamp(value, l.min, l.max, clientSettings.playbackScrollLeftOffsetPercent))
}

export function setDeviceName(value: string): void {
  const name = value.trim()
  if (name) clientSettings.deviceName = name
}

export function setAutoSelectNextSeconds(value: unknown): void {
  const l = SETTING_LIMITS.autoSelectNextSeconds
  clientSettings.autoSelectNextSeconds = round2(clamp(value, l.min, l.max, clientSettings.autoSelectNextSeconds))
}
