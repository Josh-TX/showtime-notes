export type SongStatus =
  | 'recording'
  | 'processing'
  | 'ready'
  | 'syncing'

export interface TimelineNote {
  id: string
  timeSeconds: number
  text: string
}

export interface Song {
  id: string
  name: string
  status: SongStatus
  durationSeconds: number | null
  freeNotes: string
  timelineNotes: TimelineNote[]
  processingProgress: number | null
  processingError: string | null
}

export interface SongSummary {
  id: string
  name: string
  status: SongStatus
  durationSeconds: number | null
}

export type AcquireMode = 'acquire-sync-start' | 'acquire-sync-middle'
export type SyncStatus = 'none' | 'syncing'
// Sub-state of SyncStatus 'syncing': 'acquiring' while searching for a lock, 'tracking' once locked on.
export type SyncPhase = 'acquiring' | 'tracking'

export interface SyncState {
  status: SyncStatus
  phase: SyncPhase | null
  targetSongId: string | null
  acquireMode: AcquireMode | null
  anchorRefSeconds: number | null
  anchorWallclockMs: number | null
  bars: ConfidenceBar[]
}

export interface ListenerInfo {
  deviceName: string | null
}

export interface ClientInfo {
  deviceName: string
}

export interface ShowInfo {
  songs: SongSummary[]
  listener: ListenerInfo
  sync: SyncState
  clients: ClientInfo[]
}

export interface ConfidenceBar {
  refSeconds: number
  score: number
}

export interface Waveform {
  peaks: { vocals: number[]; novocals: number[] }
  beats: number[]
  downbeats: number[]
}
