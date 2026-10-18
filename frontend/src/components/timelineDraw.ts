// Tiling + waveform drawing shared by Timeline.vue (ready songs) and RecordingTimeline.vue (live recordings).
import type { Waveform } from '../types'

export const PEAKS_PER_SECOND = 30
export const WAVEFORM_LANE_HEIGHT = 120
const NORMAL_BEAT_ALPHA = 0.08
const DOWNBEAT_ALPHA = 0.23
// opaque equivalents of #4a9eff / #7a7a7a at 50% over the #050506 background
const VOCALS_COLOR = '#44536a'
const NOVOCALS_COLOR = '#464240'
const LOUDNESS_COLOR = '#4d4d5a'
// bars drawn slightly wider than their spacing so neighbors overlap (opaque, so no gaps or alpha buildup)
const WAVEFORM_BAR_WIDTH_SCALE = 1.3

// Loudness contrast: each bar is rescaled against the last LOUDNESS_WINDOW_SECONDS, so a song that only varies
// between 90% and 100% still fills the height. hi = window's 95th percentile (never below LOUDNESS_MIN_HI, so quiet
// stretches stay small); lo = window's 5th percentile, but never above LOUDNESS_MAX_LO_FRACTION of hi, which caps how
// much a nearly-flat signal gets stretched. LOUDNESS_CURVE then pushes mid-levels down to widen the top end.
const LOUDNESS_WINDOW_SECONDS = 20
const LOUDNESS_MIN_HI = 0.5
const LOUDNESS_MAX_LO_FRACTION = 0.6
const LOUDNESS_CURVE = 2
// With no history the relative scale is meaningless (the first bar always reads as a spike), so the first bars use
// the absolute dB shape() from the new-recording modal, crossfading to the relative scale over this many seconds.
const LOUDNESS_BLEND_SECONDS = 3

// Bar height is linear in dB, in two segments: a steep one from SILENCE_DB (0) to KNEE_DB (KNEE_HEIGHT), then a flatter
// one up to CEIL_DB (1). Stateless, so bars never change once drawn. The server sends levels as dB mapped from
// SERVER_FLOOR_DB..SERVER_CEIL_DB onto 0..1 (audio_buffer.level_from_samples); undo that to get dB back.
export const SERVER_FLOOR_DB = -65
const SERVER_CEIL_DB = -5
const SILENCE_DB = -55
const KNEE_DB = -20
const CEIL_DB = -5
const KNEE_HEIGHT = 0.8
export function shape(level: number): number {
  const db = SERVER_FLOOR_DB + level * (SERVER_CEIL_DB - SERVER_FLOOR_DB)
  if (db <= SILENCE_DB) return 0
  if (db <= KNEE_DB) return ((db - SILENCE_DB) / (KNEE_DB - SILENCE_DB)) * KNEE_HEIGHT
  return Math.min(1, KNEE_HEIGHT + ((db - KNEE_DB) / (CEIL_DB - KNEE_DB)) * (1 - KNEE_HEIGHT))
}

// Browsers cap canvas size (Safari/iOS: ~16.7M px total area), so wide layers are split into fixed-width tiles.
export const TILE_WIDTH_PX = 2048

export interface Tile {
  index: number
  left: number
  width: number
}

export function computeTiles(widthPx: number): Tile[] {
  const total = Math.ceil(widthPx)
  const count = Math.ceil(total / TILE_WIDTH_PX)
  return Array.from({ length: count }, (_, index) => ({
    index,
    left: index * TILE_WIDTH_PX,
    width: Math.min(TILE_WIDTH_PX, total - index * TILE_WIDTH_PX),
  }))
}

// Sizes/clears a tile canvas and shifts the origin so callers draw in whole-canvas x coordinates.
export function prepareTile(canvas: HTMLCanvasElement | null, tile: Tile, heightPx: number): CanvasRenderingContext2D | null {
  if (!canvas) return null
  canvas.width = tile.width
  canvas.height = heightPx
  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.translate(-tile.left, 0)
  return ctx
}

// Beats first (full height) so the opaque peaks paint over them, then the vocals and novocals lanes.
export function drawWaveformTile(
  ctx: CanvasRenderingContext2D,
  tile: Tile,
  heightPx: number,
  pixelsPerSecond: number,
  waveform: Waveform,
): void {
  const right = tile.left + tile.width
  const downbeatSet = new Set(waveform.downbeats)
  ctx.globalAlpha = NORMAL_BEAT_ALPHA
  ctx.fillStyle = '#e0c33e'
  for (const beat of waveform.beats) {
    if (downbeatSet.has(beat)) continue
    const x = Math.round(beat * pixelsPerSecond)
    if (x >= tile.left && x < right) ctx.fillRect(x, 0, 1, heightPx)
  }
  ctx.globalAlpha = DOWNBEAT_ALPHA
  for (const beat of waveform.downbeats) {
    const x = Math.round(beat * pixelsPerSecond)
    if (x >= tile.left && x < right) ctx.fillRect(x, 0, 1, heightPx)
  }
  ctx.globalAlpha = 1

  const step = pixelsPerSecond / PEAKS_PER_SECOND
  const half = WAVEFORM_LANE_HEIGHT / 2
  // bars overlap into the next tile by up to one bar width, so start a couple of bars early
  const first = Math.max(0, Math.floor(tile.left / step) - 2)
  const last = Math.ceil(right / step)
  const drawPeaks = (peaks: number[], center: number, color: string) => {
    ctx.fillStyle = color
    for (let i = first; i <= last && i < peaks.length; i++) {
      const h = Math.min(1, peaks[i]) * half
      ctx.fillRect(i * step, center - h, Math.max(1, step * WAVEFORM_BAR_WIDTH_SCALE), Math.max(1, h * 2))
    }
  }
  drawPeaks(waveform.peaks.vocals, half, VOCALS_COLOR)
  drawPeaks(waveform.peaks.novocals, WAVEFORM_LANE_HEIGHT + half, NOVOCALS_COLOR)
}

// Appends contrast-stretched values to `out` for any raw peaks not yet processed. Each bar's scale depends only on
// the bars before it, so already-computed values never change; `out` is reset if `raw` restarted.
export function stretchLoudness(raw: number[], out: number[], peaksPerSecond: number): void {
  const windowPeaks = LOUDNESS_WINDOW_SECONDS * peaksPerSecond
  if (raw.length < out.length) out.length = 0
  for (let i = out.length; i < raw.length; i++) {
    const window = raw.slice(Math.max(0, i - windowPeaks + 1), i + 1).sort((a, b) => a - b)
    const hi = Math.max(window[Math.floor((window.length - 1) * 0.95)], LOUDNESS_MIN_HI)
    const lo = Math.min(window[Math.floor((window.length - 1) * 0.05)], hi * LOUDNESS_MAX_LO_FRACTION)
    const relative = Math.min(1, Math.max(0, (raw[i] - lo) / (hi - lo))) ** LOUDNESS_CURVE
    const mix = Math.min(1, i / (LOUDNESS_BLEND_SECONDS * peaksPerSecond))
    out.push((1 - mix) * shape(raw[i]) + mix * relative)
  }
}

// Single loudness trace spanning both lanes (2 * lane height), for a live recording.
export function drawLoudnessTile(
  ctx: CanvasRenderingContext2D,
  tile: Tile,
  pixelsPerSecond: number,
  peaks: number[],
  peaksPerSecond: number,
): void {
  const step = pixelsPerSecond / peaksPerSecond
  const right = tile.left + tile.width
  const half = WAVEFORM_LANE_HEIGHT
  const first = Math.max(0, Math.floor(tile.left / step) - 2)
  const last = Math.ceil(right / step)
  ctx.fillStyle = LOUDNESS_COLOR
  for (let i = first; i <= last && i < peaks.length; i++) {
    const h = Math.min(1, peaks[i]) * half
    ctx.fillRect(i * step, half - h, Math.max(1, step), Math.max(1, h * 2))
  }
}
