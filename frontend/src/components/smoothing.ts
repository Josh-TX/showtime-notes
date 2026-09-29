// Tunables for position-bar / auto-scroll smoothing. Change here.
export const SCROLL_BLEND_MS = 500 // auto-scroll (re)engaging: glide from current scroll to the position
export const SMALL_MOVE_MS = 200 // new anchor shifts position by < FADE_THRESHOLD_SECONDS: glide bar there
export const FADE_MS = 500 // new anchor shifts position by >= threshold: crossfade old bar -> new bar
export const FADE_THRESHOLD_SECONDS = 0.1

// smoothstep; swap this to change every tween's curve
export function ease(t: number): number {
  const c = Math.max(0, Math.min(1, t))
  return c * c * (3 - 2 * c)
}

export interface Anchor {
  refSeconds: number
  wallclockMs: number
}

export interface BarState {
  position: number
  opacity: number
}

export interface SmoothedFrame {
  // Primary (new) bar first, then the fading-out old bar during a crossfade
  bars: BarState[]
  primaryPosition: number | null
  // Where auto-scroll should put the position bar this frame, null = don't touch scroll
  scrollPosition: number | null
}

export interface FrameOptions {
  autoScroll: boolean
  scrollSeconds: number
  durationSeconds: number
}

type Transition = { kind: 'move'; offsetSeconds: number; startMs: number } | { kind: 'fade'; from: Anchor; startMs: number }

function extrapolate(anchor: Anchor, nowMs: number): number {
  return anchor.refSeconds + (nowMs - anchor.wallclockMs) / 1000
}

export class PositionSmoother {
  private anchor: Anchor | null = null
  private transition: Transition | null = null
  private following = false
  private scrollBlend: { startSeconds: number; startMs: number } | null = null

  reset(): void {
    this.anchor = null
    this.transition = null
    this.following = false
    this.scrollBlend = null
  }

  update(nowMs: number, anchor: Anchor | null, opts: FrameOptions): SmoothedFrame {
    if (!sameAnchor(anchor, this.anchor)) this.onAnchorChange(nowMs, anchor)

    const current = this.current(nowMs)
    if (current === null) {
      this.following = false
      this.scrollBlend = null
      return { bars: [], primaryPosition: null, scrollPosition: null }
    }
    const clamp = (s: number) => (opts.durationSeconds > 0 ? Math.max(0, Math.min(opts.durationSeconds, s)) : Math.max(0, s))
    const smoothed = clamp(current.smoothed)

    const followingNow = opts.autoScroll
    if (followingNow && !this.following) this.scrollBlend = { startSeconds: opts.scrollSeconds, startMs: nowMs }
    this.following = followingNow

    let scrollPosition: number | null = null
    if (followingNow) {
      scrollPosition = smoothed
      if (this.scrollBlend) {
        const t = (nowMs - this.scrollBlend.startMs) / SCROLL_BLEND_MS
        if (t >= 1) this.scrollBlend = null
        else scrollPosition = this.scrollBlend.startSeconds + (smoothed - this.scrollBlend.startSeconds) * ease(t)
      }
    }

    return {
      bars: current.bars.map((b) => ({ position: clamp(b.position), opacity: b.opacity })),
      primaryPosition: clamp(current.primary),
      scrollPosition,
    }
  }

  // Unclamped visual state at nowMs from the current anchor + transition; null with no anchor
  private current(nowMs: number): { bars: BarState[]; primary: number; smoothed: number } | null {
    const anchor = this.anchor
    if (!anchor) return null
    const target = extrapolate(anchor, nowMs)
    const tr = this.transition
    if (tr?.kind === 'move') {
      const t = (nowMs - tr.startMs) / SMALL_MOVE_MS
      if (t < 1) {
        const pos = target + tr.offsetSeconds * (1 - ease(t))
        return { bars: [{ position: pos, opacity: 1 }], primary: pos, smoothed: pos }
      }
    } else if (tr?.kind === 'fade') {
      const t = (nowMs - tr.startMs) / FADE_MS
      if (t < 1) {
        const e = ease(t)
        const old = extrapolate(tr.from, nowMs)
        return {
          bars: [
            { position: target, opacity: e },
            { position: old, opacity: 1 - e },
          ],
          primary: target,
          smoothed: old + (target - old) * e,
        }
      }
    }
    this.transition = null
    return { bars: [{ position: target, opacity: 1 }], primary: target, smoothed: target }
  }

  private onAnchorChange(nowMs: number, next: Anchor | null): void {
    // What's on screen right now (mid-transition included) becomes the start of the new transition
    const visual = this.current(nowMs)?.smoothed
    this.anchor = next ? { ...next } : null
    this.transition = null
    if (visual === undefined || !next) return
    const diff = visual - extrapolate(next, nowMs)
    if (Math.abs(diff) >= FADE_THRESHOLD_SECONDS) {
      this.transition = { kind: 'fade', from: { refSeconds: visual, wallclockMs: nowMs }, startMs: nowMs }
    } else if (diff !== 0) {
      this.transition = { kind: 'move', offsetSeconds: diff, startMs: nowMs }
    }
  }
}

function sameAnchor(a: Anchor | null, b: Anchor | null): boolean {
  if (a === null || b === null) return a === b
  return a.refSeconds === b.refSeconds && a.wallclockMs === b.wallclockMs
}
