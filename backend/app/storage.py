"""On-disk layout for a show's songs.

backend/data/
  show.json                        - song order (ids) + show-level settings
  songs/{id}/meta.json              - Song model (name, status, free/timeline notes, duration)
  songs/{id}/original.aac           - full mix, transcoded post-processing
  songs/{id}/vocals.aac
  songs/{id}/novocals.aac
  songs/{id}/peaks.json             - {"vocals": [...], "novocals": [...]} waveform peaks, one value per pixel-ish step
  songs/{id}/beats.json             - {"beats": [...], "downbeats": [...]} seconds
  songs/{id}/chroma.npy             - precomputed reference chroma features (float32, (n_frames, FEATURE_DIM)), for sync
"""
import json

import numpy as np

from .config import SHOW_FILE, SONGS_DIR
from .models import Song


def song_dir(song_id: str, create: bool = False):
    d = SONGS_DIR / song_id
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def meta_path(song_id: str):
    return song_dir(song_id) / "meta.json"


def audio_path(song_id: str, stem: str):
    return song_dir(song_id) / f"{stem}.aac"


def peaks_path(song_id: str):
    return song_dir(song_id) / "peaks.json"


def beats_path(song_id: str):
    return song_dir(song_id) / "beats.json"


def chroma_path(song_id: str):
    return song_dir(song_id) / "chroma.npy"


def save_song_meta(song: Song) -> None:
    meta_path(song.id).write_text(song.model_dump_json())


def load_song_meta(song_id: str) -> Song:
    return Song.model_validate_json(meta_path(song_id).read_text())


def delete_song(song_id: str) -> None:
    import shutil

    d = song_dir(song_id)
    if d.exists():
        shutil.rmtree(d)


def save_peaks(song_id: str, vocals: list[float], novocals: list[float]) -> None:
    peaks_path(song_id).write_text(json.dumps({"vocals": vocals, "novocals": novocals}))


def load_peaks(song_id: str) -> dict:
    p = peaks_path(song_id)
    return json.loads(p.read_text()) if p.exists() else {"vocals": [], "novocals": []}


def save_beats(song_id: str, beats: list[float], downbeats: list[float]) -> None:
    beats_path(song_id).write_text(json.dumps({"beats": beats, "downbeats": downbeats}))


def load_beats(song_id: str) -> dict:
    p = beats_path(song_id)
    return json.loads(p.read_text()) if p.exists() else {"beats": [], "downbeats": []}


def save_chroma(song_id: str, features: np.ndarray) -> None:
    np.save(chroma_path(song_id), features)


def load_chroma(song_id: str) -> np.ndarray:
    return np.load(chroma_path(song_id))


def save_show(song_order: list[str], acquire_start_range_seconds: float, recent_notes: list[dict]) -> None:
    SHOW_FILE.write_text(json.dumps({
        "songOrder": song_order,
        "acquireStartRangeSeconds": acquire_start_range_seconds,
        "recentNotes": recent_notes,
    }))


def load_show() -> dict:
    if not SHOW_FILE.exists():
        return {"songOrder": [], "acquireStartRangeSeconds": 20.0, "recentNotes": []}
    return json.loads(SHOW_FILE.read_text())
