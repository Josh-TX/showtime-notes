"""Owns the active sync target: acquiring/tracking against a chosen song's precomputed reference chroma, fed by the
listener's live audio. Selecting a new target (or explicitly stopping) always wins over whatever was active before.
"""
import time

from . import chroma, storage, ws_manager
from .aligner import LiveAligner, StepEvent
from .config import CAPTURE_SR
from .models import AcquireMode, ConfidenceBar, SongStatus, SyncCandidate, SyncPhase, SyncState, SyncStatus
from .resample import StreamResampler
from .state import state

SONG_END_MARGIN_SECONDS = 0.15


async def start_sync(song_id: str, mode: AcquireMode, viewport_lo_s: float | None = None, viewport_hi_s: float | None = None) -> None:
    if song_id not in state.songs:
        raise ValueError("no such song")
    if state.songs[song_id].status not in (SongStatus.READY, SongStatus.SYNCING):
        raise ValueError("song is not ready to sync")

    ref_features = storage.load_chroma(song_id)
    if mode == AcquireMode.START:
        lo, hi = 0.0, state.acquire_start_range_seconds
    else:
        if viewport_lo_s is None or viewport_hi_s is None:
            raise ValueError("acquire-sync-middle requires a viewport range")
        lo, hi = viewport_lo_s, viewport_hi_s

    await _clear_previous_target(except_song_id=song_id)

    state.live_aligner = LiveAligner(ref_features, lo, hi)
    state.chroma_stream = chroma.ChromaStream()
    state.chroma_resampler = StreamResampler(CAPTURE_SR, chroma.SR)
    state.sync = SyncState(status=SyncStatus.SYNCING, phase=SyncPhase.ACQUIRING, target_song_id=song_id, acquire_mode=mode)

    song = state.songs[song_id]
    song.status = SongStatus.SYNCING
    await state.save_and_broadcast_song(song)
    await state.broadcast_show()


async def stop_sync() -> None:
    await _clear_previous_target(except_song_id=None)
    state.live_aligner = None
    state.chroma_stream = None
    state.chroma_resampler = None
    state.sync = SyncState()
    await state.broadcast_show()


async def _clear_previous_target(except_song_id: str | None) -> None:
    prev_id = state.sync.target_song_id
    if prev_id and prev_id != except_song_id and prev_id in state.songs:
        song = state.songs[prev_id]
        if song.status == SongStatus.SYNCING:
            song.status = SongStatus.READY
            await state.save_and_broadcast_song(song)


async def feed_live_audio(samples_int16) -> None:
    """Called for every listener audio chunk. No-op unless a sync target is active."""
    if state.chroma_stream is None or state.live_aligner is None or state.chroma_resampler is None:
        return
    float_samples = samples_int16.astype("float32") / 32768.0
    resampled = state.chroma_resampler.push(float_samples)
    if len(resampled) == 0:
        return
    new_frames = state.chroma_stream.push(resampled)
    if len(new_frames) == 0:
        return
    for event in state.live_aligner.push(new_frames):
        await _handle_step_event(event)


async def _handle_step_event(event: StepEvent) -> None:
    song_id = state.sync.target_song_id
    if song_id is None:
        return

    phase = SyncPhase.TRACKING if event.mode == "tracking" else SyncPhase.ACQUIRING
    state.sync.phase = phase

    if event.mode == "tracking" and event.position_seconds is not None:
        state.sync.anchor_ref_seconds = event.position_seconds
    else:
        state.sync.anchor_ref_seconds = None
    state.sync.wallclock_ms = time.time() * 1000
    bars = [{"refSeconds": b.ref_seconds, "score": b.score} for b in event.bars]
    state.sync.bars = [ConfidenceBar(ref_seconds=b.ref_seconds, score=b.score) for b in event.bars]

    candidates = event.candidates if phase == SyncPhase.ACQUIRING else []
    best_candidates = [
        {"barIndex": c.bar_index, "score": c.score, "leftMargin": c.left_margin, "rightMargin": c.right_margin} for c in candidates
    ]
    state.sync.best_candidates = [
        SyncCandidate(bar_index=c.bar_index, score=c.score, left_margin=c.left_margin, right_margin=c.right_margin)
        for c in candidates
    ]

    await ws_manager.manager.broadcast(
        "sync_update",
        {
            "targetSongId": song_id,
            "phase": phase.value,
            "anchorRefSeconds": state.sync.anchor_ref_seconds,
            "wallclockMs": state.sync.wallclock_ms,
            "bars": bars,
            "bestCandidates": best_candidates,
        },
    )

    # song.status stays SYNCING through both phases; only the (infrequent) phase transition needs a show_update
    # so the song list / sync indicator can pick up the new color.
    if event.just_locked or event.just_dropped:
        await state.broadcast_show()

    if event.mode == "tracking" and event.position_seconds is not None:
        song = state.songs.get(song_id)
        if song and song.duration_seconds and event.position_seconds >= song.duration_seconds - SONG_END_MARGIN_SECONDS:
            await _advance_autoplay()


async def _advance_autoplay() -> None:
    song_id = state.sync.target_song_id
    if song_id is None or song_id not in state.song_order:
        await stop_sync()
        return
    idx = state.song_order.index(song_id)
    if idx + 1 >= len(state.song_order):
        await stop_sync()
        return
    next_id = state.song_order[idx + 1]
    if state.songs[next_id].status != SongStatus.READY:
        await stop_sync()
        return
    await start_sync(next_id, AcquireMode.START)
