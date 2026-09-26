import { defineStore } from 'pinia'
import { api } from '../api'
import { ws } from '../ws'
import type { ConfidenceBar, Song, ShowInfo, SongSummary, Waveform } from '../types'

const HAS_AUDIO_STATUSES = new Set(['ready', 'acquiring-sync', 'synced'])

export const useShowStore = defineStore('show', {
  state: () => ({
    deviceName: '',
    connected: false,
    show: null as ShowInfo | null,
    selectedSongId: null as string | null,
    selectedSong: null as Song | null,
    waveform: null as Waveform | null,
    positionSeconds: null as number | null,
    confidenceBars: [] as ConfidenceBar[],
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
      })
      ws.on('song_update', (payload: Song) => this._onSongUpdate(payload))
      ws.on('position_update', (payload: { targetSongId: string; positionSeconds: number }) => {
        if (payload.targetSongId === this.selectedSongId) this.positionSeconds = payload.positionSeconds
      })
      ws.on('confidence_bars', (payload: { targetSongId: string; bars: ConfidenceBar[] }) => {
        if (payload.targetSongId === this.selectedSongId) this.confidenceBars = payload.bars
      })
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
      }
    },

    async selectSong(id: string): Promise<void> {
      this.selectedSongId = id
      this.positionSeconds = null
      this.confidenceBars = []
      this.waveform = null
      this.selectedSong = await api.getSong(id)
      if (HAS_AUDIO_STATUSES.has(this.selectedSong.status)) {
        this.waveform = await api.getWaveform(id)
      }
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
