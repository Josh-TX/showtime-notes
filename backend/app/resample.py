"""Minimal streaming linear resampler (int16/float32 mono), phase-continuous across arbitrarily-sized pushes."""
import numpy as np


class StreamResampler:
    def __init__(self, src_sr: int, dst_sr: int) -> None:
        self.src_sr = src_sr
        self.dst_sr = dst_sr
        self._prev_sample = 0.0
        self._in_count = 0  # total input samples consumed so far (index of the sample *after* _prev_sample)
        self._next_out_k = 0  # index of the next output sample to produce

    def push(self, chunk: np.ndarray) -> np.ndarray:
        """chunk: float32 mono samples at src_sr, continuing the stream. Returns float32 mono samples at dst_sr."""
        window = np.concatenate([[self._prev_sample], chunk])
        out = []
        k = self._next_out_k
        while True:
            x = k * self.src_sr / self.dst_sr - (self._in_count - 1)
            floor_idx = int(x)
            if floor_idx + 1 >= len(window):
                break
            frac = x - floor_idx
            out.append(window[floor_idx] * (1 - frac) + window[floor_idx + 1] * frac)
            k += 1
        self._prev_sample = float(chunk[-1]) if len(chunk) else self._prev_sample
        self._in_count += len(chunk)
        self._next_out_k = k
        return np.asarray(out, dtype=np.float32)
