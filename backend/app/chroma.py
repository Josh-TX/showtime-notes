"""Streaming chroma feature extraction, ported from aligner-cli/features.py.

Same math as the offline research version, restructured to consume audio incrementally: ChromaStream.push()
accepts any chunk size and returns however many complete frames that chunk completes, retaining only the unconsumed
audio tail (< N_FFT samples) plus a short history of per-frame RMS values (for the causal relative-loudness
percentile) between calls. Nothing later than "now" is ever read, so this produces exactly the same frames as
compute_chroma() would for the same audio, just delivered as it arrives.

N_FFT here is half of aligner-cli's tuned offline value (4096 -> 2048): better time resolution for realtime
tracking, at some cost to low-note frequency resolution, per prior aligner-cli experimentation.
"""
from collections import deque

import numpy as np

SR = 22050
N_FFT = 2048
HOP = 1102  # ~50ms at SR; also the live position-broadcast cadence
FMIN = 65.0
FMAX = 5000.0
COMPRESSION = 5.0

LEVEL_QUIET_RMS = 1e-3
LEVEL_LOUD_RMS = 4e-3

LOUDNESS_WINDOW_SECONDS = 8.0
LOUDNESS_WEIGHT = 0.6

FEATURE_DIM = 13  # 12 chroma pitch classes + 1 relative loudness
FRAME_SECONDS = HOP / SR

_window = np.hanning(N_FFT).astype(np.float32)
_amp_scale = 2.0 / float(_window.sum())
_freqs = np.fft.rfftfreq(N_FFT, 1.0 / SR)
_band = (_freqs >= FMIN) & (_freqs <= FMAX)
_pitch_class = np.round(69 + 12 * np.log2(_freqs[_band] / 440.0)).astype(int) % 12
_fold = np.eye(12, dtype=np.float32)[_pitch_class]

_center_off = (N_FFT - HOP) // 2
_loudness_window_frames = max(1, round(LOUDNESS_WINDOW_SECONDS * SR / HOP))


def frame_center_seconds(frame: float) -> float:
    return (frame * HOP + N_FFT / 2) / SR


def _frames_to_chroma(frames: np.ndarray) -> np.ndarray:
    rms = np.sqrt(np.mean(np.square(frames), axis=1, keepdims=True))
    ramp = np.log(LEVEL_LOUD_RMS / LEVEL_QUIET_RMS)
    p = np.clip(np.log(np.maximum(rms, 1e-12) / LEVEL_QUIET_RMS) / ramp, 0.0, 1.0)
    spec = np.abs(np.fft.rfft(frames * _window, axis=1))[:, _band] * _amp_scale
    pc = np.log1p(COMPRESSION * (spec @ _fold))
    pc -= pc.mean(axis=1, keepdims=True)
    norm = np.linalg.norm(pc, axis=1, keepdims=True)
    chroma = np.where(norm > 1e-6, pc / np.maximum(norm, 1e-6), 0.0)
    return (p * chroma).astype(np.float32)


def _frames_to_local_rms(frames: np.ndarray) -> np.ndarray:
    sub = frames[:, _center_off : _center_off + HOP]
    return np.sqrt(np.mean(np.square(sub), axis=1)).astype(np.float64)


def compute_chroma(audio: np.ndarray) -> np.ndarray:
    """Whole-signal offline features for mono SR-rate float audio -> (n_frames, FEATURE_DIM) float32.
    Used to precompute a reference song's chroma once during processing."""
    stream = ChromaStream()
    return stream.push(audio, flush_tail=False)


class ChromaStream:
    """Causal, incremental chroma extractor. Feed it audio chunks of any size via push(); it returns the frames
    that became complete, holding onto only the unconsumed tail and a small causal RMS history in between calls."""

    def __init__(self) -> None:
        self._tail = np.zeros(0, dtype=np.float32)
        self._rms_history: deque[float] = deque(maxlen=_loudness_window_frames - 1)
        self.frames_emitted = 0

    def push(self, audio: np.ndarray, flush_tail: bool = False) -> np.ndarray:
        """audio: mono float32 at SR. Returns (n, FEATURE_DIM) of newly-completed frames (n may be 0)."""
        buf = np.concatenate([self._tail, audio.astype(np.float32, copy=False)])
        n_frames = max(0, (len(buf) - N_FFT) // HOP + 1)
        if n_frames == 0:
            self._tail = buf
            return np.zeros((0, FEATURE_DIM), dtype=np.float32)

        idx = np.arange(n_frames) * HOP
        raw_frames = np.stack([buf[i : i + N_FFT] for i in idx])
        chroma = _frames_to_chroma(raw_frames)
        local_rms = _frames_to_local_rms(raw_frames)

        loudness = np.empty(n_frames, dtype=np.float32)
        ramp_denom = max(1, _loudness_window_frames - 1)
        for i in range(n_frames):
            history = self._rms_history
            count = len(history) + 1
            rank = sum(1 for v in history if v <= local_rms[i]) + 1
            loudness[i] = LOUDNESS_WEIGHT * (2.0 * (rank / count) - 1.0)
            history.append(float(local_rms[i]))
        del ramp_denom

        self._tail = buf[n_frames * HOP :]
        self.frames_emitted += n_frames
        return np.concatenate([chroma, loudness[:, None]], axis=1)
