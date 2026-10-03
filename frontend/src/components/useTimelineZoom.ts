import { nextTick, onMounted, onUnmounted, type Ref } from 'vue'
import { clientSettings, setTimelineWidthSeconds } from '../store/clientSettings'

const WHEEL_DELTA_CLAMP = 50
const WHEEL_SENSITIVITY = 0.005
const LINE_DELTA_PX = 16

interface ZoomOptions {
  containerEl: Ref<HTMLElement | null>
  startWidthPx: () => number
  pixelsPerSecond: () => number
  // True when something else (auto-scroll / follow-live) re-positions the scroll after a zoom
  scrollIsDriven: () => boolean
}

// Safari desktop pinch fires non-standard gesture events instead of ctrl+wheel
interface GestureEvent extends UIEvent {
  scale: number
  clientX: number
}

export function isZoomWheel(event: WheelEvent): boolean {
  return event.ctrlKey || event.metaKey
}

// Zooming = changing timelineWidthSeconds (seconds visible per container width). The time under the
// cursor/pinch center stays put unless scrollIsDriven() says the scroll is managed elsewhere.
export function useTimelineZoom(options: ZoomOptions): void {
  let pending: { time: number; focalX: number } | null = null
  let gestureStartSeconds = 0

  function zoomTo(seconds: number, focalX: number): void {
    const el = options.containerEl.value
    if (!el) return
    if (!pending && !options.scrollIsDriven()) {
      const time = (el.scrollLeft + focalX - options.startWidthPx()) / options.pixelsPerSecond()
      pending = { time, focalX }
      nextTick(() => {
        if (!pending) return
        el.scrollLeft = options.startWidthPx() + pending.time * options.pixelsPerSecond() - pending.focalX
        pending = null
      })
    }
    setTimelineWidthSeconds(seconds)
  }

  function focalXFor(clientX: number): number {
    return clientX - (options.containerEl.value?.getBoundingClientRect().left ?? 0)
  }

  function onWheel(event: WheelEvent): void {
    if (!isZoomWheel(event)) return
    event.preventDefault() // also blocks browser page zoom
    const delta = event.deltaMode === 1 ? event.deltaY * LINE_DELTA_PX : event.deltaY
    const clamped = Math.max(-WHEEL_DELTA_CLAMP, Math.min(WHEEL_DELTA_CLAMP, delta))
    // wheel up (negative) = zoom in = fewer seconds visible
    zoomTo(clientSettings.timelineWidthSeconds * Math.exp(clamped * WHEEL_SENSITIVITY), focalXFor(event.clientX))
  }

  function onGestureStart(event: Event): void {
    event.preventDefault()
    gestureStartSeconds = clientSettings.timelineWidthSeconds
  }
  function onGestureChange(event: Event): void {
    event.preventDefault()
    const g = event as GestureEvent
    if (g.scale > 0) zoomTo(gestureStartSeconds / g.scale, focalXFor(g.clientX))
  }
  function onGestureEnd(event: Event): void {
    event.preventDefault()
  }

  onMounted(() => {
    const el = options.containerEl.value
    if (!el) return
    el.addEventListener('wheel', onWheel, { passive: false })
    el.addEventListener('gesturestart', onGestureStart)
    el.addEventListener('gesturechange', onGestureChange)
    el.addEventListener('gestureend', onGestureEnd)
  })
  onUnmounted(() => {
    const el = options.containerEl.value
    if (!el) return
    el.removeEventListener('wheel', onWheel)
    el.removeEventListener('gesturestart', onGestureStart)
    el.removeEventListener('gesturechange', onGestureChange)
    el.removeEventListener('gestureend', onGestureEnd)
  })
}
