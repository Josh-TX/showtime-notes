"""Recording -> song processing pipeline: WAV wrap -> Demucs (vocals/no-vocals) + beat_this (beats/downbeats) ->
waveform peaks -> AAC transcode for storage -> reference chroma for sync. Runs off the event loop thread (all of
this is blocking CPU/GPU work); progress is reported back via callback so the caller can broadcast it.

Demucs and beat_this both read WAV natively (torchaudio/soundfile) - no ffmpeg needed for that step. ffmpeg is only
used at the end, to transcode the three final WAVs to AAC for compact, browser-compatible storage/playback.
"""
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Callable

import numpy as np

from . import chroma, storage
from .config import CAPTURE_SR, STORAGE_BITRATE_KBPS

PEAKS_PER_SECOND = 30
NORMALIZE_PERCENTILE = 98
# Normalization gain ramps (log-space) with the percentile RMS (linear): at/below NO_SCALE_BELOW (~-40 dBFS) no
# scaling, so quiet stems (e.g. demucs bleed on instrumental songs) stay flat; at/above FULL_SCALE_ABOVE (~-26 dBFS)
# full scaling so the percentile reaches 1.0.
NO_SCALE_BELOW = 0.01
FULL_SCALE_ABOVE = 0.05

ProgressCB = Callable[[float, str], None]  # (fraction done, what's happening next)


def _write_wav(path: Path, pcm_int16: np.ndarray, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm_int16.tobytes())


def _load_wav_mono_float(path: Path) -> tuple[np.ndarray, int]:
    import torchaudio

    tensor, sr = torchaudio.load(str(path))
    mono = tensor.mean(dim=0).numpy().astype(np.float32)
    return mono, sr


def _separate_vocals(wav_path: Path, out_dir: Path) -> tuple[Path, Path]:
    import demucs.separate

    demucs.separate.main(["--two-stems", "vocals", "-n", "htdemucs", "-o", str(out_dir), str(wav_path)])
    stem_dir = out_dir / "htdemucs" / wav_path.stem
    return stem_dir / "vocals.wav", stem_dir / "no_vocals.wav"


def _detect_beats(wav_path: Path) -> tuple[list[float], list[float]]:
    import torch
    from beat_this.inference import File2Beats

    device = "cuda" if torch.cuda.is_available() else "cpu"
    f2b = File2Beats(checkpoint_path="final0", device=device)
    beats, downbeats = f2b(str(wav_path))
    return [float(b) for b in beats], [float(d) for d in downbeats]


def _peaks(mono: np.ndarray, sr: int) -> list[float]:
    bucket = max(1, int(sr / PEAKS_PER_SECOND))
    n_buckets = max(1, len(mono) // bucket)
    trimmed = mono[: n_buckets * bucket].reshape(n_buckets, bucket)
    rms = np.sqrt(np.mean(np.square(trimmed), axis=1))
    percentile = float(np.percentile(rms, NORMALIZE_PERCENTILE))
    if percentile > 0:
        ramp = (percentile - NO_SCALE_BELOW) / (FULL_SCALE_ABOVE - NO_SCALE_BELOW)
        ramp = min(max(ramp, 0.0), 1.0)
        rms = np.clip(rms * (1.0 / percentile) ** ramp, 0.0, 1.0)
    return [round(float(v), 4) for v in rms]


def _transcode_aac(src_wav: Path, dst_aac: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(src_wav),
            "-ac", "1", "-c:a", "aac", "-b:a", f"{STORAGE_BITRATE_KBPS}k",
            str(dst_aac),
        ],
        check=True,
    )


def process_recording(song_id: str, pcm_int16: np.ndarray, on_progress: ProgressCB) -> float:
    """Blocking. Returns the song's duration in seconds. Raises on failure (caller handles/broadcasts the error)."""
    with tempfile.TemporaryDirectory(prefix="showtime-notes-") as tmp:
        tmp_dir = Path(tmp)
        original_wav = tmp_dir / "original.wav"
        _write_wav(original_wav, pcm_int16, CAPTURE_SR)
        duration_seconds = len(pcm_int16) / CAPTURE_SR
        on_progress(0.05, "detecting beats")

        beats, downbeats = _detect_beats(original_wav)
        on_progress(0.1, "splitting vocals and novocals")

        vocals_wav, novocals_wav = _separate_vocals(original_wav, tmp_dir / "separated")
        on_progress(0.75, "computing waveforms")

        vocals_mono, vocals_sr = _load_wav_mono_float(vocals_wav)
        novocals_mono, novocals_sr = _load_wav_mono_float(novocals_wav)
        storage.save_peaks(song_id, _peaks(vocals_mono, vocals_sr), _peaks(novocals_mono, novocals_sr))
        storage.save_beats(song_id, beats, downbeats)
        on_progress(0.8, "computing chroma")

        original_mono, original_sr = _load_wav_mono_float(original_wav)
        resampled = _resample(original_mono, original_sr, chroma.SR)
        storage.save_chroma(song_id, chroma.compute_chroma(resampled))
        on_progress(0.85, "compressing audio")

        _transcode_aac(original_wav, storage.audio_path(song_id, "original"))
        _transcode_aac(vocals_wav, storage.audio_path(song_id, "vocals"))
        _transcode_aac(novocals_wav, storage.audio_path(song_id, "novocals"))
        on_progress(1.0, "done")

    return duration_seconds


def _resample(mono: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    if src_sr == dst_sr:
        return mono
    duration = len(mono) / src_sr
    n_dst = int(round(duration * dst_sr))
    src_x = np.linspace(0.0, duration, num=len(mono), endpoint=False)
    dst_x = np.linspace(0.0, duration, num=n_dst, endpoint=False)
    return np.interp(dst_x, src_x, mono).astype(np.float32)
