import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from . import recording, storage, sync_service
from .models import ApiModel, AcquireMode, Song, TrackNote
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


class TrackNoteBody(ApiModel):
    time_seconds: float
    text: str


@router.post("/songs/{song_id}/track-notes")
async def add_track_note(song_id: str, body: TrackNoteBody):
    song = _song_or_404(song_id)
    note = TrackNote(id=uuid.uuid4().hex[:12], time_seconds=body.time_seconds, text=body.text)
    song.track_notes.append(note)
    await state.save_and_broadcast_song(song)
    return note.model_dump(by_alias=True)


class UpdateTrackNoteBody(ApiModel):
    time_seconds: float | None = None
    text: str | None = None


@router.put("/songs/{song_id}/track-notes/{note_id}")
async def update_track_note(song_id: str, note_id: str, body: UpdateTrackNoteBody):
    song = _song_or_404(song_id)
    note = next((n for n in song.track_notes if n.id == note_id), None)
    if note is None:
        raise HTTPException(404, "no such track note")
    if body.time_seconds is not None:
        note.time_seconds = body.time_seconds
    if body.text is not None:
        note.text = body.text
    await state.save_and_broadcast_song(song)
    return note.model_dump(by_alias=True)


@router.delete("/songs/{song_id}/track-notes/{note_id}")
async def delete_track_note(song_id: str, note_id: str):
    song = _song_or_404(song_id)
    song.track_notes = [n for n in song.track_notes if n.id != note_id]
    await state.save_and_broadcast_song(song)
    return {"ok": True}


# -- recording --

class StartRecordingBody(ApiModel):
    include_pre_roll: bool = True


@router.post("/recording/start")
async def start_recording(body: StartRecordingBody):
    try:
        song = await recording.start_recording(body.include_pre_roll)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return song.model_dump(by_alias=True)


@router.post("/recording/stop")
async def stop_recording():
    try:
        song = await recording.stop_recording()
    except ValueError as e:
        raise HTTPException(409, str(e))
    return song.model_dump(by_alias=True)


@router.post("/recording/discard")
async def discard_recording():
    try:
        await recording.discard_recording()
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ok": True}


class ConfirmRecordingBody(ApiModel):
    name: str


@router.post("/recording/confirm")
async def confirm_recording(body: ConfirmRecordingBody):
    try:
        song = await recording.confirm_and_process(body.name)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return song.model_dump(by_alias=True)


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
