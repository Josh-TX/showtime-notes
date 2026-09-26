"""In-memory audio buffers for the listener's live PCM stream. Both operate on mono int16 samples at
config.CAPTURE_SR; audio never touches disk until a recording is stopped and named."""
import numpy as np

from .config import CAPTURE_SR, RECORDING_MAX_SECONDS, ROLLING_BUFFER_SECONDS


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
    Lives only in memory - a server crash mid-recording is accepted as an acceptable loss."""

    def __init__(self) -> None:
        self._capacity = int(RECORDING_MAX_SECONDS * CAPTURE_SR)
        self._buf = np.zeros(0, dtype=np.int16)

    def push(self, samples: np.ndarray) -> None:
        self._buf = np.concatenate([self._buf, samples])
        if len(self._buf) > self._capacity:
            self._buf = self._buf[-self._capacity :]

    @property
    def duration_seconds(self) -> float:
        return len(self._buf) / CAPTURE_SR

    def all_samples(self) -> np.ndarray:
        return self._buf.copy()
