export type SongStatus =
  | 'recording'
  | 'processing'
  | 'ready'
  | 'syncing'

export type NoteColor =
  | 'light-red'
  | 'light-orange'
  | 'light-yellow'
  | 'light-green'
  | 'light-blue'
  | 'light-purple'
  | 'light-pink'
  | 'white'
  | 'gray'
  | 'red'
  | 'orange'
  | 'yellow'
  | 'green'
  | 'blue'
  | 'purple'
  | 'pink'
  | 'light-gray'
  | 'dark-gray'
  | 'dark-red'
  | 'dark-orange'
  | 'dark-yellow'
  | 'dark-green'
  | 'dark-blue'
  | 'dark-purple'
  | 'dark-pink'
  | 'silver'
  | 'black'
  | 'brown'

export interface TimelineNote {
  id: string
  timeSeconds: number
  y: number // px from timeline top to the note's top edge
  text: string
  color: NoteColor
}

export interface FavoriteNote {
  id: string
  text: string
  color: NoteColor
}

export interface Song {
  id: string
  name: string
  status: SongStatus
  durationSeconds: number | null
  freeNotes: string
  timelineNotes: TimelineNote[]
  processingProgress: number | null
  processingMessage: string | null
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

export interface SyncCandidate {
  barIndex: number
  score: number
  leftMargin: number
  rightMargin: number
}

export interface SyncState {
  status: SyncStatus
  phase: SyncPhase | null
  targetSongId: string | null
  acquireMode: AcquireMode | null
  anchorRefSeconds: number | null
  wallclockMs: number | null
  bars: ConfidenceBar[]
  bestCandidates: SyncCandidate[]
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
  favorites: FavoriteNote[][] // one list per column, top to bottom
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
