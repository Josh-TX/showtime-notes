import { defineStore } from 'pinia'
import { api } from '../api'
import { ws } from '../ws'
import type { ConfidenceBar, Song, ShowInfo, SongSummary, SyncPhase, Waveform } from '../types'

const HAS_AUDIO_STATUSES = new Set(['ready', 'syncing'])

function anchorFromSync(sync: { anchorRefSeconds: number | null; anchorWallclockMs: number | null }) {
  return sync.anchorRefSeconds !== null && sync.anchorWallclockMs !== null
    ? { refSeconds: sync.anchorRefSeconds, wallclockMs: sync.anchorWallclockMs }
    : null
}

export const useShowStore = defineStore('show', {
  state: () => ({
    deviceName: '',
    connected: false,
    show: null as ShowInfo | null,
    selectedSongId: null as string | null,
    selectedSong: null as Song | null,
    isStartingRecording: false,
    waveform: null as Waveform | null,
    recordingPeaks: [] as number[],
    positionAnchor: null as { refSeconds: number; wallclockMs: number } | null,
    confidenceBars: [] as ConfidenceBar[],
    syncPhase: null as SyncPhase | null,
    loudness: 0,
    isListener: false,
    wantsLiveAudio: false,
  }),
  actions: {
    connect(deviceName: string): void {
      this.deviceName = deviceName
      ws.on('show_update', (payload: ShowInfo) => {
        this.show = payload
        if (payload.listener.deviceName !== deviceName) this.isListener = false
        if (this.selectedSongId && !payload.songs.some((s) => s.id === this.selectedSongId)) {
          this.selectedSongId = null
          this.selectedSong = null
          this.waveform = null
          this.recordingPeaks = []
        }
        if (this.isStartingRecording) {
          const recordingSong = payload.songs.find((s) => s.status === 'recording')
          if (recordingSong) {
            this.isStartingRecording = false
            this.selectSong(recordingSong.id)
          }
        }
        if (payload.sync.targetSongId !== this.selectedSongId) {
          this.positionAnchor = null
          this.confidenceBars = []
          this.syncPhase = null
        } else {
          this.positionAnchor = anchorFromSync(payload.sync)
          this.confidenceBars = payload.sync.bars
          this.syncPhase = payload.sync.phase
        }
      })
      ws.on('song_update', (payload: Song) => this._onSongUpdate(payload))
      ws.on('recording_peaks', (payload: { songId: string; peaks: number[] }) => {
        if (payload.songId === this.selectedSongId) this.recordingPeaks.push(...payload.peaks)
      })
      ws.on(
        'sync_update',
        (payload: {
          targetSongId: string
          phase: SyncPhase
          anchorRefSeconds: number | null
          anchorWallclockMs: number | null
          bars: ConfidenceBar[]
        }) => {
          if (payload.targetSongId !== this.selectedSongId) return
          this.positionAnchor = anchorFromSync(payload)
          this.confidenceBars = payload.bars
          this.syncPhase = payload.phase
        },
      )
      ws.on('loudness', (payload: { level: number }) => {
        this.loudness = payload.level
      })
      ws.connect(deviceName)
      this.connected = true
      api.getState().then((state) => (this.show = state))
    },

    _onSongUpdate(song: Song): void {
      if (this.show) {
        const idx = this.show.songs.findIndex((s) => s.id === song.id)
        const summary: SongSummary = {
          id: song.id,
          name: song.name,
          status: song.status,
          durationSeconds: song.durationSeconds,
        }
        if (idx >= 0) this.show.songs[idx] = summary
      }
      if (this.selectedSongId === song.id) {
        const hadAudio = this.waveform !== null
        this.selectedSong = song
        if (!hadAudio && HAS_AUDIO_STATUSES.has(song.status)) {
          api.getWaveform(song.id).then((w) => (this.waveform = w))
        }
        if (song.status !== 'recording') this.recordingPeaks = []
      }
    },

    async selectSong(id: string): Promise<void> {
      this.isStartingRecording = false
      this.selectedSongId = id
      if (this.show?.sync.targetSongId === id) {
        this.positionAnchor = anchorFromSync(this.show.sync)
        this.confidenceBars = this.show.sync.bars
        this.syncPhase = this.show.sync.phase
      } else {
        this.positionAnchor = null
        this.confidenceBars = []
        this.syncPhase = null
      }
      this.waveform = null
      this.recordingPeaks = []
      this.selectedSong = await api.getSong(id)
      if (HAS_AUDIO_STATUSES.has(this.selectedSong.status)) {
        this.waveform = await api.getWaveform(id)
      } else if (this.selectedSong.status === 'recording') {
        this.recordingPeaks = (await api.getRecordingPeaks(id)).peaks
      }
    },

    openStartRecording(): void {
      this.isStartingRecording = true
      this.selectedSongId = null
      this.selectedSong = null
      this.waveform = null
      this.recordingPeaks = []
      this.positionAnchor = null
      this.confidenceBars = []
      this.syncPhase = null
    },
    cancelStartRecording(): void {
      this.isStartingRecording = false
    },

    becomeListener(): void {
      ws.send('become_listener')
      this.isListener = true
    },
    releaseListener(): void {
      ws.send('release_listener')
      this.isListener = false
    },
    setLiveAudioSubscription(wanted: boolean): void {
      this.wantsLiveAudio = wanted
      ws.send('set_live_audio_subscription', { wanted })
    },
  },
})
