"""Recording lifecycle: start (optionally seeded with the rolling pre-roll buffer) -> the take is named while still
recording -> stop-and-save (kicks off processing) or stop-and-discard (thrown away immediately, no processing).
Managed by any client - not tied to a particular websocket connection, so it survives a client disconnecting
mid-take."""
import asyncio
import uuid

from . import processing, storage, ws_manager
from .audio_buffer import RecordingBuffer
from .models import Song, SongStatus
from .state import state


def is_recording() -> bool:
    return state.recording is not None


async def start_recording(include_pre_roll: bool, name: str | None = None) -> Song:
    if state.recording is not None:
        raise ValueError("a recording is already in progress")
    state.recording = RecordingBuffer()
    state.recording_pre_roll_included = include_pre_roll
    if include_pre_roll:
        state.recording.push(state.rolling_buffer.snapshot())

    song = Song(
        id=uuid.uuid4().hex[:12],
        name=(name or "").strip() or "New Recording",
        status=SongStatus.RECORDING,
    )
    state.recording_song_id = song.id
    state.songs[song.id] = song
    state.song_order.append(song.id)
    storage.song_dir(song.id, create=True)
    storage.save_song_meta(song)
    state.persist_show()
    await state.broadcast_show()
    return song


async def push_audio(samples) -> None:
    """Called from the listener audio-ingestion route for every chunk while a recording is active."""
    if state.recording is None or state.recording_song_id is None:
        return
    new_peaks = state.recording.push(samples)
    if new_peaks:
        await ws_manager.manager.broadcast(
            "recording_peaks", {"songId": state.recording_song_id, "peaks": new_peaks}
        )


async def stop_and_discard() -> None:
    if state.recording is None or state.recording_song_id is None:
        raise ValueError("no recording in progress")
    song_id = state.recording_song_id
    state.recording = None
    state.recording_song_id = None
    state.songs.pop(song_id, None)
    if song_id in state.song_order:
        state.song_order.remove(song_id)
    storage.delete_song(song_id)
    state.persist_show()
    await state.broadcast_show()


async def stop_and_save(name: str) -> Song:
    if state.recording is None or state.recording_song_id is None:
        raise ValueError("no recording in progress")
    if not name.strip():
        raise ValueError("a name is required to save a recording")
    song_id = state.recording_song_id
    song = state.songs[song_id]
    song.name = name.strip()
    song.status = SongStatus.PROCESSING
    song.processing_progress = 0.0
    song.processing_error = None
    duration = state.recording.duration_seconds
    pcm = state.recording.all_samples()
    state.recording = None
    state.recording_song_id = None
    song.duration_seconds = duration
    await state.save_and_broadcast_song(song)

    asyncio.create_task(_run_processing(song_id, pcm))
    return song


async def _report_progress(song_id: str, progress: float) -> None:
    song = state.songs.get(song_id)
    if song is None:
        return
    song.processing_progress = progress
    await state.broadcast_song(song_id)


async def _run_processing(song_id: str, pcm) -> None:
    loop = asyncio.get_event_loop()

    def on_progress(progress: float) -> None:
        asyncio.run_coroutine_threadsafe(_report_progress(song_id, progress), loop)

    try:
        duration = await asyncio.to_thread(processing.process_recording, song_id, pcm, on_progress)
        song = state.songs[song_id]
        song.status = SongStatus.READY
        song.duration_seconds = duration
        song.processing_progress = None
        song.processing_error = None
        await state.save_and_broadcast_song(song)
    except Exception as e:
        song = state.songs[song_id]
        song.processing_progress = None
        song.processing_error = str(e)
        await state.save_and_broadcast_song(song)
