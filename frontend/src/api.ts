import type { AcquireMode, FavoriteNote, NoteColor, Song, ShowInfo, TimelineNote, Waveform } from './types'

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(`${method} ${path} failed: ${res.status} ${await res.text()}`)
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

export const api = {
  getState: () => request<ShowInfo>('GET', '/state'),
  getSong: (id: string) => request<Song>('GET', `/songs/${id}`),
  getWaveform: (id: string) => request<Waveform>('GET', `/songs/${id}/waveform`),
  getRecordingPeaks: (id: string) => request<{ peaks: number[] }>('GET', `/songs/${id}/recording-peaks`),
  audioUrl: (id: string, stem: 'original' | 'vocals' | 'novocals') => `/api/songs/${id}/audio/${stem}`,

  renameSong: (id: string, name: string) => request<Song>('POST', `/songs/${id}/rename`, { name }),
  deleteSong: (id: string) => request<void>('DELETE', `/songs/${id}`),
  reorderSongs: (songIds: string[]) => request<void>('POST', '/songs/reorder', { songIds }),
  setFreeNotes: (id: string, text: string) => request<Song>('PUT', `/songs/${id}/free-notes`, { text }),
  addTimelineNote: (id: string, note: { timeSeconds: number; y: number; text: string; color: NoteColor }) =>
    request<TimelineNote>('POST', `/songs/${id}/timeline-notes`, note),
  updateTimelineNote: (
    id: string,
    noteId: string,
    patch: { timeSeconds?: number; y?: number; text?: string; color?: NoteColor },
  ) =>
    request<TimelineNote>('PUT', `/songs/${id}/timeline-notes/${noteId}`, patch),
  deleteTimelineNote: (id: string, noteId: string) => request<void>('DELETE', `/songs/${id}/timeline-notes/${noteId}`),

  addFavorite: (fav: { column: number; index: number; text: string; color: NoteColor }) =>
    request<FavoriteNote>('POST', '/favorites', fav),
  moveFavorite: (id: string, column: number, index: number) =>
    request<void>('PUT', `/favorites/${id}/move`, { column, index }),
  updateFavorite: (id: string, patch: { text?: string; color?: NoteColor }) =>
    request<FavoriteNote>('PUT', `/favorites/${id}`, patch),
  deleteFavorite: (id: string) => request<void>('DELETE', `/favorites/${id}`),

  getRecordingPreview: () =>
    request<{ endTsMs: number; endPeakIndex: number; peaksPerSecond: number; peaks: number[] }>('GET', '/recording/preview'),
  startRecording: (name: string, clickTsMs: number, offsetSeconds: number) =>
    request<Song>('POST', '/recording/start', { name, clickTsMs, offsetSeconds }),
  stopAndSaveRecording: (name: string) => request<Song>('POST', '/recording/stop-and-save', { name }),
  stopAndDiscardRecording: () => request<void>('POST', '/recording/stop-and-discard'),

  startSync: (songId: string, mode: AcquireMode, viewportLoSeconds?: number, viewportHiSeconds?: number) =>
    request<ShowInfo>('POST', '/sync/start', { songId, mode, viewportLoSeconds, viewportHiSeconds }),
  stopSync: () => request<ShowInfo>('POST', '/sync/stop'),

  setAcquireStartRange: (seconds: number) => request<void>('PUT', '/settings/acquire-start-range', { seconds }),
}
