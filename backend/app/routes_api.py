import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from . import recording, storage, sync_service
from .audio_buffer import LIVE_PEAKS_PER_SECOND
from .models import AcquireMode, ApiModel, FavoriteNote, NoteColor, Song, TimelineNote
from .state import state

router = APIRouter(prefix="/api")


def _song_or_404(song_id: str) -> Song:
    song = state.songs.get(song_id)
    if song is None:
        raise HTTPException(404, "no such song")
    return song


# -- general / song info --

@router.get("/state")
async def get_state():
    return state.to_show_info().model_dump(by_alias=True)


@router.get("/songs/{song_id}")
async def get_song(song_id: str):
    return _song_or_404(song_id).model_dump(by_alias=True)


@router.get("/songs/{song_id}/waveform")
async def get_waveform(song_id: str):
    _song_or_404(song_id)
    peaks = storage.load_peaks(song_id)
    beats = storage.load_beats(song_id)
    return {"peaks": peaks, "beats": beats["beats"], "downbeats": beats["downbeats"]}


@router.get("/songs/{song_id}/recording-peaks")
async def get_recording_peaks(song_id: str):
    _song_or_404(song_id)
    if state.recording is None or state.recording_song_id != song_id:
        return {"peaks": []}
    return {"peaks": state.recording.peaks}


@router.get("/songs/{song_id}/audio/{stem}")
async def get_audio(song_id: str, stem: str):
    _song_or_404(song_id)
    if stem not in ("original", "vocals", "novocals"):
        raise HTTPException(404, "no such audio stem")
    path = storage.audio_path(song_id, stem)
    if not path.exists():
        raise HTTPException(404, "audio not available yet")
    return FileResponse(path, media_type="audio/aac")


# -- song mutation --

class RenameBody(ApiModel):
    name: str


@router.post("/songs/{song_id}/rename")
async def rename_song(song_id: str, body: RenameBody):
    song = _song_or_404(song_id)
    song.name = body.name
    await state.save_and_broadcast_song(song)
    return song.model_dump(by_alias=True)


@router.delete("/songs/{song_id}")
async def delete_song(song_id: str):
    _song_or_404(song_id)
    if song_id == state.recording_song_id:
        raise HTTPException(409, "cannot delete a song that is currently recording")
    state.songs.pop(song_id, None)
    if song_id in state.song_order:
        state.song_order.remove(song_id)
    if state.sync.target_song_id == song_id:
        await sync_service.stop_sync()
    storage.delete_song(song_id)
    state.persist_show()
    await state.broadcast_show()
    return {"ok": True}


class ReorderBody(ApiModel):
    song_ids: list[str]


@router.post("/songs/reorder")
async def reorder_songs(body: ReorderBody):
    if set(body.song_ids) != set(state.song_order):
        raise HTTPException(400, "songIds must be a permutation of the current song order")
    state.song_order = body.song_ids
    state.persist_show()
    await state.broadcast_show()
    return {"ok": True}


class FreeNotesBody(ApiModel):
    text: str


@router.put("/songs/{song_id}/free-notes")
async def set_free_notes(song_id: str, body: FreeNotesBody):
    song = _song_or_404(song_id)
    song.free_notes = body.text
    await state.save_and_broadcast_song(song)
    return song.model_dump(by_alias=True)


MAX_NOTE_TEXT_LENGTH = 200


def _clean_note_text(text: str) -> str:
    text = text.strip()
    if len(text) > MAX_NOTE_TEXT_LENGTH:
        raise HTTPException(400, f"note text must be at most {MAX_NOTE_TEXT_LENGTH} characters")
    return text


class TimelineNoteBody(ApiModel):
    time_seconds: float
    y: float
    text: str
    color: NoteColor


@router.post("/songs/{song_id}/timeline-notes")
async def add_timeline_note(song_id: str, body: TimelineNoteBody):
    song = _song_or_404(song_id)
    text = _clean_note_text(body.text)
    note = TimelineNote(
        id=uuid.uuid4().hex[:12],
        time_seconds=max(0.0, body.time_seconds),
        y=max(0.0, body.y),
        text=text,
        color=body.color,
    )
    song.timeline_notes.append(note)
    await state.save_and_broadcast_song(song)
    return note.model_dump(by_alias=True)


class UpdateTimelineNoteBody(ApiModel):
    time_seconds: float | None = None
    y: float | None = None
    text: str | None = None
    color: NoteColor | None = None


@router.put("/songs/{song_id}/timeline-notes/{note_id}")
async def update_timeline_note(song_id: str, note_id: str, body: UpdateTimelineNoteBody):
    song = _song_or_404(song_id)
    note = next((n for n in song.timeline_notes if n.id == note_id), None)
    if note is None:
        raise HTTPException(404, "no such timeline note")
    if body.time_seconds is not None:
        note.time_seconds = max(0.0, body.time_seconds)
    if body.y is not None:
        note.y = max(0.0, body.y)
    if body.text is not None:
        note.text = _clean_note_text(body.text)
    if body.color is not None:
        note.color = body.color
    await state.save_and_broadcast_song(song)
    return note.model_dump(by_alias=True)


@router.delete("/songs/{song_id}/timeline-notes/{note_id}")
async def delete_timeline_note(song_id: str, note_id: str):
    song = _song_or_404(song_id)
    song.timeline_notes = [n for n in song.timeline_notes if n.id != note_id]
    await state.save_and_broadcast_song(song)
    return {"ok": True}


# -- favorites (shared by all clients; fixed columns, each an ordered list) --


def _favorite_column(column: int) -> list[FavoriteNote]:
    if not 0 <= column < len(state.favorites):
        raise HTTPException(400, f"column must be 0-{len(state.favorites) - 1}")
    return state.favorites[column]


def _find_favorite(favorite_id: str) -> tuple[list[FavoriteNote], FavoriteNote]:
    for column in state.favorites:
        for fav in column:
            if fav.id == favorite_id:
                return column, fav
    raise HTTPException(404, "no such favorite")


async def _favorites_changed() -> None:
    state.persist_show()
    await state.broadcast_show()


class AddFavoriteBody(ApiModel):
    column: int
    index: int
    text: str
    color: NoteColor


@router.post("/favorites")
async def add_favorite(body: AddFavoriteBody):
    column = _favorite_column(body.column)
    fav = FavoriteNote(id=uuid.uuid4().hex[:12], text=_clean_note_text(body.text), color=body.color)
    column.insert(max(0, body.index), fav)
    await _favorites_changed()
    return fav.model_dump(by_alias=True)


class MoveFavoriteBody(ApiModel):
    column: int
    index: int  # position within the destination column once the favorite has been removed from its old spot


@router.put("/favorites/{favorite_id}/move")
async def move_favorite(favorite_id: str, body: MoveFavoriteBody):
    dest = _favorite_column(body.column)
    source, fav = _find_favorite(favorite_id)
    source.remove(fav)
    dest.insert(max(0, body.index), fav)
    await _favorites_changed()
    return {"ok": True}


class UpdateFavoriteBody(ApiModel):
    text: str | None = None
    color: NoteColor | None = None


@router.put("/favorites/{favorite_id}")
async def update_favorite(favorite_id: str, body: UpdateFavoriteBody):
    _, fav = _find_favorite(favorite_id)
    if body.text is not None:
        fav.text = _clean_note_text(body.text)
    if body.color is not None:
        fav.color = body.color
    await _favorites_changed()
    return fav.model_dump(by_alias=True)


@router.delete("/favorites/{favorite_id}")
async def delete_favorite(favorite_id: str):
    column, fav = _find_favorite(favorite_id)
    column.remove(fav)
    await _favorites_changed()
    return {"ok": True}


# -- recording --

class StartRecordingBody(ApiModel):
    name: str | None = None
    click_ts_ms: float
    offset_seconds: float = 0.0


@router.get("/recording/preview")
async def recording_preview():
    """The rolling buffer's recent loudness, for the new-recording modal."""
    buf = state.rolling_buffer
    return {
        "endTsMs": buf.end_ts_ms,
        "endPeakIndex": buf.end_peak_index,
        "peaksPerSecond": LIVE_PEAKS_PER_SECOND,
        "peaks": buf.peaks(),
    }


@router.post("/recording/start")
async def start_recording(body: StartRecordingBody):
    try:
        start_ts_ms = body.click_ts_ms - max(0.0, body.offset_seconds) * 1000.0
        song = await recording.start_recording(body.name, start_ts_ms)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return song.model_dump(by_alias=True)


class StopAndSaveBody(ApiModel):
    name: str


@router.post("/recording/stop-and-save")
async def stop_and_save_recording(body: StopAndSaveBody):
    try:
        song = await recording.stop_and_save(body.name)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return song.model_dump(by_alias=True)


@router.post("/recording/stop-and-discard")
async def stop_and_discard_recording():
    try:
        await recording.stop_and_discard()
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ok": True}


# -- sync --

class StartSyncBody(ApiModel):
    song_id: str
    mode: AcquireMode
    viewport_lo_seconds: float | None = None
    viewport_hi_seconds: float | None = None


@router.post("/sync/start")
async def start_sync(body: StartSyncBody):
    try:
        await sync_service.start_sync(body.song_id, body.mode, body.viewport_lo_seconds, body.viewport_hi_seconds)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return state.to_show_info().model_dump(by_alias=True)


@router.post("/sync/stop")
async def stop_sync():
    await sync_service.stop_sync()
    return state.to_show_info().model_dump(by_alias=True)


class AcquireStartRangeBody(ApiModel):
    seconds: float


@router.put("/settings/acquire-start-range")
async def set_acquire_start_range(body: AcquireStartRangeBody):
    state.acquire_start_range_seconds = body.seconds
    state.persist_show()
    await state.broadcast_show()
    return {"ok": True}
