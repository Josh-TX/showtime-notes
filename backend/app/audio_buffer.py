"""In-memory audio buffers for the listener's live PCM stream. Both operate on mono int16 samples at
config.CAPTURE_SR; audio never touches disk until a recording is stopped and named."""
import numpy as np

from .config import CAPTURE_SR, RECORDING_MAX_SECONDS, ROLLING_BUFFER_SECONDS

LIVE_PEAKS_PER_SECOND = 50
_PEAK_WINDOW_SAMPLES = int(CAPTURE_SR / LIVE_PEAKS_PER_SECOND)

FLOOR_DB = -70.0
CEIL_DB = -10.0


def level_from_samples(samples_int16: np.ndarray) -> float:
    """Normalize a chunk of mono int16 samples to a 0-1 loudness level (same dB scale used for the navbar meter)."""
    rms = float(np.sqrt(np.mean(np.square(samples_int16.astype(np.float32))))) / 32768.0
    db = 20.0 * np.log10(rms) if rms > 0 else FLOOR_DB
    return max(0.0, min(1.0, (db - FLOOR_DB) / (CEIL_DB - FLOOR_DB)))


class RollingBuffer:
    """Always-on ~1s ring of the most recent live audio: recording pre-roll + (indirectly, via whatever consumes
    it live) the chroma stream's lookback. Never grows past its cap."""

    def __init__(self, seconds: float = ROLLING_BUFFER_SECONDS) -> None:
        self._capacity = int(seconds * CAPTURE_SR)
        self._buf = np.zeros(0, dtype=np.int16)

    def push(self, samples: np.ndarray) -> None:
        self._buf = np.concatenate([self._buf, samples])
        if len(self._buf) > self._capacity:
            self._buf = self._buf[-self._capacity :]

    def snapshot(self) -> np.ndarray:
        return self._buf.copy()


class RecordingBuffer:
    """A single in-progress take. Capped at RECORDING_MAX_SECONDS; rotates out (drops) the oldest audio past that.
    Lives only in memory - a server crash mid-recording is accepted as an acceptable loss.

    Also maintains a coarse live-amplitude peaks trace (one value per 1/LIVE_PEAKS_PER_SECOND) for clients to render
    a live waveform while recording, since the real vocals/novocals split can only be computed offline."""

    def __init__(self) -> None:
        self._capacity = int(RECORDING_MAX_SECONDS * CAPTURE_SR)
        self._buf = np.zeros(0, dtype=np.int16)
        self._peak_capacity = int(RECORDING_MAX_SECONDS * LIVE_PEAKS_PER_SECOND)
        self._peaks: list[float] = []
        self._peak_leftover = np.zeros(0, dtype=np.int16)

    def push(self, samples: np.ndarray) -> list[float]:
        self._buf = np.concatenate([self._buf, samples])
        if len(self._buf) > self._capacity:
            self._buf = self._buf[-self._capacity :]

        self._peak_leftover = np.concatenate([self._peak_leftover, samples])
        new_peaks: list[float] = []
        while len(self._peak_leftover) >= _PEAK_WINDOW_SAMPLES:
            window = self._peak_leftover[:_PEAK_WINDOW_SAMPLES]
            self._peak_leftover = self._peak_leftover[_PEAK_WINDOW_SAMPLES:]
            new_peaks.append(level_from_samples(window))
        if new_peaks:
            self._peaks.extend(new_peaks)
            if len(self._peaks) > self._peak_capacity:
                self._peaks = self._peaks[-self._peak_capacity :]
        return new_peaks

    @property
    def duration_seconds(self) -> float:
        return len(self._buf) / CAPTURE_SR

    @property
    def peaks(self) -> list[float]:
        return list(self._peaks)

    def all_samples(self) -> np.ndarray:
        return self._buf.copy()
