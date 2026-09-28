"""Realtime chroma aligner: dense-template-matching acquisition + tracking, ported from aligner-cli/tracker.py.

Differences from that offline research harness (both deliberate, for the live server):
  - Operates on a small rolling ring of recent live frames (LIVE_RING_SECONDS) instead of a fully precomputed live
    array - matches.txt's constraint that no multi-second raw-audio/feature buffer is kept beyond what a step needs.
  - Acquisition's scan range is a parameter (acquire_lo_s, acquire_hi_s) instead of a fixed "first N seconds of ref",
    so both acquire-sync-start (first ACQUIRE_START_RANGE_SECONDS) and acquire-sync-middle (user's current
    viewport) reuse the same code.
  - A sustained low-confidence streak while tracking drops back to "acquiring" (rescanning the same range
    indefinitely) instead of terminating the run - there is no failure state, only acquiring/tracking.
"""
from dataclasses import dataclass, field

import numpy as np

from .chroma import FEATURE_DIM, FRAME_SECONDS, frame_center_seconds

UPDATE_FRAMES = 10  # aligner steps every this many new live frames (~500ms)

ACQUIRE_START_RANGE_SECONDS = 20.0  # default scan range for acquire-sync-start; configurable per show

ACQUIRE_WINDOW_SECONDS = 10.0
ACQ_RECENCY_TIERS = ((0.25, 8.0), (0.25, 4.0))  # newest quarter counts 8x, next quarter 4x, older half weighs 1.0
ACQ_MIN_SCORE, ACQ_MIN_LEFT_MARGIN, ACQ_MIN_RIGHT_MARGIN = 0.35, 0.10, 0.02
LOCK_AGREE_SECONDS = 1.0
AGREE_TOL_FRAMES = 3

TRACK_WINDOW_SECONDS = 10.0
TRACK_RECENCY_TIERS = ((0.25, 8.0), (0.25, 4.0))
TRACK_RADIUS_SECONDS = 3.0  # also: the +/-3s confidence-bar window while synced
TRACK_MIN_SCORE = 0.30
TRACK_ADJACENT_FRAMES = 2
TRACK_ADJACENT_SWITCH_GAIN = 0.01
TRACK_JUMP_SWITCH_GAIN = 0.15
TRACK_FAIL_STREAK = 6  # consecutive low-confidence updates before dropping back to acquiring

EXCLUSION_FRAMES = 10

LIVE_RING_SECONDS = TRACK_WINDOW_SECONDS + 2.0  # a little slack beyond the largest window any step reads


def frames(seconds: float) -> int:
    return int(round(seconds / FRAME_SECONDS))


def _window_scores(ref: np.ndarray, pad: int, live_win: np.ndarray, weights: np.ndarray, j_lo: int, j_hi: int) -> np.ndarray:
    w = len(live_win)
    n = j_hi - j_lo + 1
    seg = ref[j_lo - (w - 1) + pad : j_hi + pad + 1]
    sim = seg @ live_win.T
    scores = np.zeros(n, dtype=np.float32)
    for m in range(w):
        scores += weights[m] * sim[m : m + n, m]
    return scores / weights.sum()


def _recency_weights(w: int, tiers) -> np.ndarray:
    weights = np.ones(w, dtype=np.float32)
    end = w
    for fraction, weight in tiers:
        start = max(0, end - int(round(fraction * w)))
        weights[start:end] = weight
        end = start
    return weights


def _analyze_peak(scores: np.ndarray, index: int | None = None) -> tuple[float, float, float]:
    b = int(np.argmax(scores)) if index is None else index
    best = float(scores[b])
    keep = np.ones(len(scores), dtype=bool)
    keep[max(0, b - EXCLUSION_FRAMES) : b + EXCLUSION_FRAMES + 1] = False
    margin = best - float(scores[keep].max()) if keep.any() else best
    frac = float(b)
    if 0 < b < len(scores) - 1:
        denom = float(scores[b - 1] - 2 * scores[b] + scores[b + 1])
        if denom < 0:
            frac += float(np.clip(0.5 * (scores[b - 1] - scores[b + 1]) / denom, -0.5, 0.5))
    return frac, best, margin


def _side_margins(scores: np.ndarray, index: int) -> tuple[float, float]:
    best = float(scores[index])
    left = scores[: max(0, index - EXCLUSION_FRAMES)]
    right = scores[index + EXCLUSION_FRAMES + 1 :]
    return (
        best - float(left.max()) if len(left) else best,
        best - float(right.max()) if len(right) else best,
    )


@dataclass
class ConfidenceBar:
    ref_seconds: float
    score: float


@dataclass
class StepEvent:
    mode: str  # 'acquiring' | 'tracking'
    just_locked: bool
    just_dropped: bool  # tracking -> acquiring (sustained low confidence)
    position_seconds: float | None  # None unless mode == 'tracking'
    bars: list[ConfidenceBar] = field(default_factory=list)


class LiveAligner:
    """One instance per (server, active sync target). Feed it ChromaStream output frames via push()."""

    def __init__(self, ref_features: np.ndarray, acquire_lo_s: float = 0.0, acquire_hi_s: float = ACQUIRE_START_RANGE_SECONDS):
        self.n_ref = len(ref_features)
        self.pad = max(frames(ACQUIRE_WINDOW_SECONDS), frames(TRACK_WINDOW_SECONDS))
        self.ref = np.concatenate([np.zeros((self.pad, FEATURE_DIM), dtype=np.float32), ref_features.astype(np.float32)])
        self.set_acquire_range(acquire_lo_s, acquire_hi_s)

        self.mode = "acquiring"
        self._run: list[tuple[int, float]] = []
        self._offset = 0.0
        self._low_streak = 0

        ring_capacity = frames(LIVE_RING_SECONDS)
        self._live = np.zeros((0, FEATURE_DIM), dtype=np.float32)
        self._ring_capacity = ring_capacity
        self._base = 0  # abs frame index of self._live[0]
        self._count = 0  # total frames ever pushed
        self._pending = 0  # frames accumulated since the last UPDATE_FRAMES step

    def set_acquire_range(self, lo_s: float, hi_s: float) -> None:
        self._acq_j_lo = max(0, frames(lo_s))
        self._acq_j_hi = min(self.n_ref - 1, max(self._acq_j_lo, frames(hi_s)))

    def push(self, new_frames: np.ndarray) -> list[StepEvent]:
        events: list[StepEvent] = []
        if len(new_frames) == 0:
            return events
        self._live = np.concatenate([self._live, new_frames])
        self._count += len(new_frames)
        self._pending += len(new_frames)
        if len(self._live) > self._ring_capacity:
            trim = len(self._live) - self._ring_capacity
            self._live = self._live[trim:]
            self._base += trim

        while self._pending >= UPDATE_FRAMES:
            self._pending -= UPDATE_FRAMES
            i_end_abs = self._count - self._pending - 1
            i_end_rel = i_end_abs - self._base
            if i_end_rel < 0:
                continue
            events.append(self._step(i_end_rel))
        return events

    def _scan_acquisition(self, i_end: int) -> dict | None:
        w = frames(ACQUIRE_WINDOW_SECONDS)
        if i_end + 1 < w:
            return None
        j_lo, j_hi = self._acq_j_lo, self._acq_j_hi
        win = self._live[i_end - w + 1 : i_end + 1]
        weights = _recency_weights(w, ACQ_RECENCY_TIERS)
        scores = _window_scores(self.ref, self.pad, win, weights, j_lo, j_hi)
        b = int(np.argmax(scores))
        j_frac, best, _ = _analyze_peak(scores, b)
        left, right = _side_margins(scores, b)
        ok = best >= ACQ_MIN_SCORE and left >= ACQ_MIN_LEFT_MARGIN and right >= ACQ_MIN_RIGHT_MARGIN
        return {"ok": ok, "j": j_lo + j_frac, "scores": scores, "j_lo": j_lo}

    def _acquire_step(self, i_end: int) -> StepEvent:
        scan = self._scan_acquisition(i_end)
        passing = scan if scan is not None and scan["ok"] else None
        if passing is not None:
            offset = passing["j"] - i_end
            if self._run and abs(offset - self._run[-1][1]) <= AGREE_TOL_FRAMES:
                self._run.append((i_end, offset))
            else:
                self._run = [(i_end, offset)]
        else:
            self._run = []

        bars = []
        if scan is not None:
            bars = [
                ConfidenceBar(frame_center_seconds(scan["j_lo"] + i), float(sc))
                for i, sc in enumerate(scan["scores"])
            ]

        if passing is not None and i_end - self._run[0][0] >= frames(LOCK_AGREE_SECONDS):
            self.mode = "tracking"
            self._offset = self._run[-1][1]
            self._low_streak = 0
            return StepEvent("tracking", True, False, frame_center_seconds(i_end + self._offset), bars)
        return StepEvent("acquiring", False, False, None, bars)

    def _track_step(self, i_end: int) -> StepEvent:
        w = min(frames(TRACK_WINDOW_SECONDS), i_end + 1)
        radius = frames(TRACK_RADIUS_SECONDS)
        center = int(round(i_end + self._offset))
        j_lo = max(0, center - radius)
        j_hi = min(self.n_ref - 1, center + radius)
        if j_hi < j_lo:
            # ran off the end of the reference song; stay put and keep reporting the last known position
            return StepEvent("tracking", False, False, frame_center_seconds(i_end + self._offset), [])

        win = self._live[i_end - w + 1 : i_end + 1]
        weights = _recency_weights(w, TRACK_RECENCY_TIERS)
        scores = _window_scores(self.ref, self.pad, win, weights, j_lo, j_hi)
        bars = [ConfidenceBar(frame_center_seconds(j_lo + i), float(sc)) for i, sc in enumerate(scores)]

        cur = int(np.clip(center - j_lo, 0, len(scores) - 1))
        cur_score = float(scores[cur])
        options = []
        adjacent = [i for d in range(1, TRACK_ADJACENT_FRAMES + 1) for i in (cur - d, cur + d) if 0 <= i < len(scores)]
        if adjacent:
            adj = max(adjacent, key=lambda i: scores[i])
            if float(scores[adj]) - cur_score >= TRACK_ADJACENT_SWITCH_GAIN:
                options.append((float(scores[adj]), adj))
        far = np.ones(len(scores), dtype=bool)
        far[max(0, cur - TRACK_ADJACENT_FRAMES) : cur + TRACK_ADJACENT_FRAMES + 1] = False
        if far.any():
            jump = int(np.argmax(np.where(far, scores, -np.inf)))
            if float(scores[jump]) - cur_score >= TRACK_JUMP_SWITCH_GAIN:
                options.append((float(scores[jump]), jump))
        pick = cur if not options else max(options)[1]
        best = float(scores[pick])

        ok = best >= TRACK_MIN_SCORE
        if ok:
            j = i_end + self._offset if pick == cur else j_lo + _analyze_peak(scores, pick)[0]
            self._offset = j - i_end
            self._low_streak = 0
            return StepEvent("tracking", False, False, frame_center_seconds(i_end + self._offset), bars)

        self._low_streak += 1
        if self._low_streak >= TRACK_FAIL_STREAK:
            self.mode = "acquiring"
            self._run = []
            self._low_streak = 0
            return StepEvent("acquiring", False, True, None, bars)
        return StepEvent("tracking", False, False, frame_center_seconds(i_end + self._offset), bars)

    def _step(self, i_end_rel: int) -> StepEvent:
        if self.mode == "acquiring":
            return self._acquire_step(i_end_rel)
        return self._track_step(i_end_rel)
