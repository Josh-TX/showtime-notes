"""Chroma feature extraction: batch/offline version of the STFT chroma used by the live aligner.

Each output frame depends only on its own N_FFT-sample window plus up to LOUDNESS_WINDOW_SECONDS of *preceding*
local-RMS history (for the relative-loudness dimension) -- never anything later in the file. So computing every
frame of a file up front (as this module does) is exactly equivalent to computing them one at a time as audio
arrives -- no future information leaks into any frame. That's what lets the CLI precompute chroma for the whole
live file and then simulate the online tracker by only ever looking at frames up to the "current" index.

All constants here are POC tuning knobs. Comments describe what moving each one does.
"""
import subprocess
from pathlib import Path

import numpy as np

SR = 22050  # sample rate everything is decoded/resampled to before framing
N_FFT = 4096  # analysis window in samples (~186 ms at SR); bigger = better low-note frequency resolution, worse time resolution
HOP = 1102  # samples between frame starts (~50 ms at SR); smaller = finer time resolution, more frames to score
FMIN = 65.0  # ~C2; FFT bins below this are excluded from the chroma fold
FMAX = 5000.0  # FFT bins above this are excluded from the chroma fold
COMPRESSION = 5.0  # log-compression strength for pitch-class energy: log(1 + COMPRESSION * amplitude); higher flattens loud/quiet differences more

# A frame's "presence" p in [0, 1] is how loud it is, ramped linearly in log-RMS from 0 at LEVEL_QUIET_RMS to 1 at
# LEVEL_LOUD_RMS. Raise both if room/mic noise between notes is being treated as sound; lower both if soft playing is
# being treated as silence. Widen the gap between them for a more gradual transition.
LEVEL_QUIET_RMS = 1e-3
LEVEL_LOUD_RMS = 4e-3

# Relative-loudness dimension: each frame's RMS (over a HOP-wide slice centered on the same instant as the chroma
# frame -- see _center_off) is ranked as a percentile against the trailing LOUDNESS_WINDOW_SECONDS of RMS history
# (less at the start of a file), then mapped from [0, 1] to [-1, 1]. This is per-file-relative (not absolute dB), so
# it identifies "loud moment for this recording" (e.g. a beat) even when comparing two files recorded at different
# overall volumes. Percentile rank is scale/monotonic-transform invariant, so it doesn't matter that RMS is linear
# rather than log here.
LOUDNESS_WINDOW_SECONDS = 8.0
LOUDNESS_WEIGHT = 0.6  # how much this [-1, 1] dim counts against unit-length chroma when folded into one direction (see compute_chroma); tune via run_suite.py

FEATURE_DIM = 13  # 12 chroma pitch classes + 1 relative loudness
BATCH_FRAMES = 512  # frames per FFT batch when precomputing a whole file; bounds peak memory, doesn't affect output

_window = np.hanning(N_FFT).astype(np.float32)
_amp_scale = 2.0 / float(_window.sum())
_freqs = np.fft.rfftfreq(N_FFT, 1.0 / SR)
_band = (_freqs >= FMIN) & (_freqs <= FMAX)
_pitch_class = np.round(69 + 12 * np.log2(_freqs[_band] / 440.0)).astype(int) % 12
_fold = np.eye(12, dtype=np.float32)[_pitch_class]  # (bins in band, 12)

_center_off = (N_FFT - HOP) // 2  # start, within an N_FFT frame, of the HOP-wide slice centered on the same instant
_loudness_window_frames = max(1, round(LOUDNESS_WINDOW_SECONDS * SR / HOP))


def frame_center_seconds(frame: float) -> float:
    """Time (in the source audio) at the center of a chroma frame; accepts fractional (sub-frame-refined) indexes."""
    return (frame * HOP + N_FFT / 2) / SR


def _frames_to_chroma(frames: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(n, N_FFT) audio frames -> (presence p (n,1) in [0,1] from RMS, unit-length mean-centered chroma direction
    (n,12)). p is folded in by the caller after combining chroma direction with the loudness dimension, so that a
    silent frame (p=0) still dots to 0 against anything."""
    rms = np.sqrt(np.mean(np.square(frames), axis=1, keepdims=True))
    ramp = np.log(LEVEL_LOUD_RMS / LEVEL_QUIET_RMS)
    p = np.clip(np.log(np.maximum(rms, 1e-12) / LEVEL_QUIET_RMS) / ramp, 0.0, 1.0)
    spec = np.abs(np.fft.rfft(frames * _window, axis=1))[:, _band] * _amp_scale
    pc = np.log1p(COMPRESSION * (spec @ _fold))
    pc -= pc.mean(axis=1, keepdims=True)
    norm = np.linalg.norm(pc, axis=1, keepdims=True)
    chroma = np.where(norm > 1e-6, pc / np.maximum(norm, 1e-6), 0.0)
    return p, chroma.astype(np.float32)


def _frames_to_local_rms(frames: np.ndarray) -> np.ndarray:
    """(n, N_FFT) audio frames -> (n,) RMS of the HOP-wide slice centered on the same instant as the chroma frame."""
    sub = frames[:, _center_off : _center_off + HOP]
    return np.sqrt(np.mean(np.square(sub), axis=1)).astype(np.float64)


def _causal_relative_loudness(local_rms: np.ndarray) -> np.ndarray:
    """(n,) RMS values -> (n,) relative-loudness dim in [-1, 1]: percentile rank of each value against itself and up
    to _loudness_window_frames - 1 preceding values (fewer at the start of the file, never later ones)."""
    n = len(local_rms)
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    w = _loudness_window_frames
    padded = np.concatenate([np.full(w - 1, -np.inf), local_rms])
    windows = np.lib.stride_tricks.sliding_window_view(padded, w)  # (n, w), row i = history for frame i
    current = windows[:, -1:]
    valid = windows > -np.inf
    percentile = np.sum((windows <= current) & valid, axis=1) / np.sum(valid, axis=1)
    return (2.0 * percentile - 1.0).astype(np.float32)


def compute_chroma(audio: np.ndarray) -> np.ndarray:
    """Whole-signal features for mono SR-rate float audio -> (n_frames, FEATURE_DIM) float32.
    Frame i covers samples [i*HOP, i*HOP + N_FFT). Processed in batches of BATCH_FRAMES frames only to bound memory;
    batch boundaries don't change any frame's value."""
    n_frames = max(0, (len(audio) - N_FFT) // HOP + 1)
    if n_frames == 0:
        return np.zeros((0, FEATURE_DIM), dtype=np.float32)
    presence = np.zeros((n_frames, 1), dtype=np.float32)
    chroma_unit = np.zeros((n_frames, 12), dtype=np.float32)
    local_rms = np.zeros(n_frames, dtype=np.float64)
    for start in range(0, n_frames, BATCH_FRAMES):
        end = min(start + BATCH_FRAMES, n_frames)
        idx = np.arange(start, end) * HOP
        batch = np.stack([audio[i : i + N_FFT] for i in idx])
        presence[start:end], chroma_unit[start:end] = _frames_to_chroma(batch)
        local_rms[start:end] = _frames_to_local_rms(batch)
    loudness_pm1 = _causal_relative_loudness(local_rms)

    # Fold chroma direction + weighted loudness into a single unit direction, then scale by presence, so every frame
    # has norm <= 1 and a dot product between two frames is bounded by (and only reaches) 1 when both are fully
    # present and identical in chroma and loudness rank -- regardless of LOUDNESS_WEIGHT.
    raw = np.concatenate([chroma_unit, (LOUDNESS_WEIGHT * loudness_pm1)[:, None]], axis=1)
    raw_norm = np.linalg.norm(raw, axis=1, keepdims=True)
    direction = np.where(raw_norm > 1e-6, raw / np.maximum(raw_norm, 1e-6), 0.0)
    return (presence * direction).astype(np.float32)


def decode_audio(path: Path) -> np.ndarray:
    """Decode any ffmpeg-readable file to mono float32 PCM at SR."""
    proc = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        check=True,
        capture_output=True,
    )
    return np.frombuffer(proc.stdout, dtype="<f4")
