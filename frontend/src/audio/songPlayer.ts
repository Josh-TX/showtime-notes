import { reactive } from 'vue'
import { api } from '../api'

export type PlayerSpeed = 1 | 2 | 3 | 4
export type Stem = 'original' | 'vocals' | 'novocals'

// Client-local song playback (not server state). One <audio> element, source swapped per song/stem.
export const songPlayer = reactive({
  songId: null as string | null,
  stem: 'original' as Stem,
  playing: false,
  position: 0,
  speed: 1 as PlayerSpeed,
})

const audio = new Audio()
audio.preload = 'auto'

audio.addEventListener('timeupdate', () => {
  songPlayer.position = audio.currentTime
})
audio.addEventListener('ended', () => {
  songPlayer.playing = false
})
audio.addEventListener('pause', () => {
  songPlayer.playing = false
})
audio.addEventListener('play', () => {
  songPlayer.playing = true
})

// rAF-smooth position while playing (timeupdate only fires ~4Hz)
function poll(): void {
  if (songPlayer.playing) songPlayer.position = audio.currentTime
  requestAnimationFrame(poll)
}
requestAnimationFrame(poll)

function load(songId: string, stem: Stem, position: number, resume: boolean): void {
  audio.src = api.audioUrl(songId, stem)
  const onReady = () => {
    audio.currentTime = position
    if (resume) void audio.play()
  }
  audio.addEventListener('loadedmetadata', onReady, { once: true })
  audio.load()
}

export function playerStop(): void {
  audio.pause()
  audio.removeAttribute('src')
  audio.load()
  songPlayer.songId = null
  songPlayer.playing = false
  songPlayer.position = 0
}

export function playerPlay(songId: string): void {
  if (songPlayer.songId !== songId) {
    songPlayer.songId = songId
    songPlayer.position = 0
    load(songId, songPlayer.stem, 0, true)
    return
  }
  // restart from 0 after reaching the end
  if (audio.ended) audio.currentTime = 0
  void audio.play()
}

export function playerPause(): void {
  audio.pause()
}

export function playerSeek(songId: string, seconds: number): void {
  songPlayer.position = seconds
  if (songPlayer.songId !== songId) {
    songPlayer.songId = songId
    load(songId, songPlayer.stem, seconds, false)
    return
  }
  audio.currentTime = seconds
}

export function playerSetStem(stem: Stem): void {
  if (songPlayer.stem === stem) return
  songPlayer.stem = stem
  if (!songPlayer.songId) return
  load(songPlayer.songId, stem, audio.currentTime, songPlayer.playing)
}

export function playerSetSpeed(speed: PlayerSpeed): void {
  songPlayer.speed = speed
  // defaultPlaybackRate survives src reloads (stem switch / song change); playbackRate alone is reset by load()
  audio.defaultPlaybackRate = speed
  audio.playbackRate = speed
}
