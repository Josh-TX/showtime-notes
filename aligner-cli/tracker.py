"""Offline live-to-ref aligner: same dense-template-matching idea as the realtime backend aligner, restructured to
run over two precomputed chroma arrays instead of a push()-fed stream.

At each simulated update, only live frames up to the current index are read -- exactly what a realtime stream would
have delivered by "now" -- so precomputing the whole live file's chroma up front is not cheating, just fast.

Differences from the realtime version, both intentional for this experimental harness:
  - No wall clock / capture timestamps; positions are in ref/live seconds directly.
  - No verify-rescan / drop back to "acquiring". Once tracking starts, a sustained low-confidence run ends the run
    (see TRACK_FAIL_STREAK) rather than resetting -- we want to know when tracking broke, not paper over it.

All thresholds below are POC tuning knobs, same as the realtime aligner; comments describe what moving each one does.
"""
from dataclasses import dataclass, field

import numpy as np

from features import FEATURE_DIM, HOP, SR

FRAME_SECONDS = HOP / SR  # duration of one chroma frame (~50 ms)

UPDATE_FRAMES = 10  # aligner steps every this many new live frames (~500 ms of live audio)

# -- initial sync (acquisition) ---------------------------------------------------------------------------------
ACQ_REF_SECONDS = 20.0  # only the first this-many seconds of the ref are searched for the initial match
# Window lengths (s) tried each update -> (min best score, min left margin, min right margin); shorter windows need a
# higher bar. Left/right margin = best score minus the best score more than EXCLUSION_FRAMES earlier/later in the ref.
# Taking an earlier match is fine, so the right margin can be low; a strong earlier rival is not, so left is strict.
ACQ_WINDOWS = {2.0: (0.40, 0.15, 0.03), 4.0: (0.35, 0.10, 0.02)}
LOCK_AGREE_SECONDS = 1.0  # passing candidates must agree on the offset for this long of live audio before locking
AGREE_TOL_FRAMES = 3  # offsets within this many frames (~150 ms) count as agreeing

# -- tracking ------------------------------------------------------------------------------------------------------
TRACK_WINDOW_SECONDS = 10.0  # how much recent live audio each candidate is scored against
# Recency weighting of that window: (fraction of the window, weight), newest first; the rest weighs 1.0.
# Newest quarter counts 8x, the next quarter 4x, the older half 1x.
TRACK_RECENCY_TIERS = ((0.25, 8.0), (0.25, 4.0))
TRACK_RADIUS_SECONDS = 3.0  # candidates: every ref frame within this many seconds either side of the predicted position
TRACK_MIN_SCORE = 0.30  # the chosen candidate's score must be at least this, else the update counts as low confidence
# Sticky choice, comparing candidates to the score at the current (predicted) position. Staying is the default;
# a switch needs the candidate to score higher than current by at least the gain below.
TRACK_ADJACENT_FRAMES = 2  # "adjacent" = within this many frames of current (+-N)
TRACK_ADJACENT_SWITCH_GAIN = 0.01  # to switch to an adjacent frame (+-TRACK_ADJACENT_FRAMES)
TRACK_JUMP_SWITCH_GAIN = 0.15  # to switch to any frame farther than TRACK_ADJACENT_FRAMES away

# POC-only (no realtime equivalent): tracking is declared failed -- and the run stops -- after this many consecutive
# low-confidence updates (score < TRACK_MIN_SCORE). Raise to tolerate longer rough patches before giving up.
TRACK_FAIL_STREAK = 6

EXCLUSION_FRAMES = 10  # frames either side of a peak ignored when looking for its rivals (~0.5 s), used during acquisition
GAIN_EXCLUSION_FRAMES = 5  # frames either side of the picked position excluded when finding its best rival, for the reported gain percentiles
JUMP_THRESHOLD_FRAMES = 5  # a relocation (picked vs. predicted position) farther than this counts as a forward/backward jump

# -- single-number tracking score (for comparing tuning runs against each other) -----------------------------------
# Weighted blend of the four gain percentiles, favoring the median but still responsive to bad tails.
GAIN_PERCENTILE_WEIGHTS = (0.4, 0.3, 0.2, 0.1)  # median, p25, p10, p5
# Anchors mapping the weighted gain above to a roughly-0-1 subscore (not clamped -- see tracking_score); calibrate
# from real runs (e.g. a self-comparison as the ceiling, a known-rough run as the floor), not derived from first
# principles.
GAIN_SCORE_FLOOR = -0.05
GAIN_SCORE_CEIL = 0.15
SCORE_GAIN_WEIGHT = 0.55  # vs. SCORE_JUMP_WEIGHT below; slight edge to gain (match quality) over jump (stability)
SCORE_JUMP_WEIGHT = 0.45


@dataclass
class TrackingScore:
    total: float  # SCORE_GAIN_WEIGHT * gain + SCORE_JUMP_WEIGHT * jump
    gain: float  # 0-100 subscore from the gain percentiles alone
    jump: float  # 0-100 subscore from jump rate/magnitude alone


def tracking_score(result: "Result") -> TrackingScore:
    """Composite 0-100 score (and its two subscores) combining gain percentiles and jump behavior, for comparing
    tuning runs. All zero if tracking failed outright or never produced gain samples (nothing to score)."""
    if result.stop_reason == "track_failed" or result.median_gain is None:
        return TrackingScore(0.0, 0.0, 0.0)
    weighted_gain = sum(
        w * g for w, g in zip(GAIN_PERCENTILE_WEIGHTS, (result.median_gain, result.p25_gain, result.p10_gain, result.p5_gain))
    )
    # Not clamped to [0, 1]: this score is for comparing tuning runs, so a run clearly better/worse than the
    # calibration anchors should read as such rather than flattening out at the ceiling/floor.
    gain_score = (weighted_gain - GAIN_SCORE_FLOOR) / (GAIN_SCORE_CEIL - GAIN_SCORE_FLOOR)

    total_jump_s = (result.avg_forward_jump_s or 0.0) * result.forward_jump_count + (
        result.avg_backward_jump_s or 0.0
    ) * result.backward_jump_count
    minutes = result.audio_seconds_processed / 60.0
    jump_rate = total_jump_s / minutes if minutes > 0 else 0.0
    jump_score = 1.0 / (1.0 + jump_rate)

    return TrackingScore(
        total=100.0 * (SCORE_GAIN_WEIGHT * gain_score + SCORE_JUMP_WEIGHT * jump_score),
        gain=100.0 * gain_score,
        jump=100.0 * jump_score,
    )


def frames(seconds: float) -> int:
    return int(round(seconds / FRAME_SECONDS))


def window_scores(ref: np.ndarray, pad: int, live_win: np.ndarray, weights: np.ndarray, j_lo: int, j_hi: int) -> np.ndarray:
    """Scores for j in [j_lo, j_hi] (ref frame aligned with the newest frame of live_win).

    ref is zero-padded at the front by `pad` frames (>= len(live_win) - 1) so windows can hang off the ref start.
    """
    w = len(live_win)
    n = j_hi - j_lo + 1
    seg = ref[j_lo - (w - 1) + pad : j_hi + pad + 1]  # row r <-> ref frame j_lo - (w-1) + r
    sim = seg @ live_win.T  # (n + w - 1, w)
    scores = np.zeros(n, dtype=np.float32)
    for m in range(w):
        scores += weights[m] * sim[m : m + n, m]
    return scores / weights.sum()


def recency_weights(w: int, tiers) -> np.ndarray:
    """Per-frame weights for a window of w frames (oldest first) from (fraction, weight) tiers, newest tier first."""
    weights = np.ones(w, dtype=np.float32)
    end = w
    for fraction, weight in tiers:
        start = max(0, end - int(round(fraction * w)))
        weights[start:end] = weight
        end = start
    return weights


def analyze_peak(scores: np.ndarray, index: int | None = None) -> tuple[float, float, float]:
    """(refined index, score, margin over the best score outside the exclusion zone) of the peak at `index`
    (default: the best score)."""
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


def side_margins(scores: np.ndarray, index: int) -> tuple[float, float]:
    """(left, right): the score at `index` minus the best score more than EXCLUSION_FRAMES to its left / right.
    A side with nothing beyond the exclusion zone has nothing to be confused with, so its margin is the score."""
    best = float(scores[index])
    left = scores[: max(0, index - EXCLUSION_FRAMES)]
    right = scores[index + EXCLUSION_FRAMES + 1 :]
    return (
        best - float(left.max()) if len(left) else best,
        best - float(right.max()) if len(right) else best,
    )


@dataclass
class TrackSnapshot:
    """One tracking-phase update, kept for the visual report."""
    live_s: float
    j_lo: int
    scores: np.ndarray
    cur_idx: int  # index into scores of the predicted (pre-update) position
    pick_idx: int  # index into scores of the chosen position


@dataclass
class Result:
    acquisition_time_s: float | None = None
    acquisition_left_margin: float | None = None
    acquisition_right_margin: float | None = None
    acquisition_window_s: float | None = None
    failed_track_timestamp_s: float | None = None
    stop_reason: str = "live_end"  # 'live_end' | 'ref_end' | 'track_failed' | 'max_duration'
    tracking_steps: int = 0
    median_gain: float | None = None
    p25_gain: float | None = None
    p10_gain: float | None = None
    p5_gain: float | None = None
    forward_jump_count: int = 0
    backward_jump_count: int = 0
    avg_forward_jump_s: float | None = None
    avg_backward_jump_s: float | None = None
    farthest_forward_jump_s: float | None = None
    farthest_backward_jump_s: float | None = None
    audio_seconds_processed: float = 0.0
    snapshots: list = field(default_factory=list)  # TrackSnapshot, for the visual report only
    gain_samples: list = field(default_factory=list, repr=False)  # scratch; percentiles computed from this at the end
    forward_jump_samples: list = field(default_factory=list, repr=False)  # seconds; scratch for forward jump stats
    backward_jump_samples: list = field(default_factory=list, repr=False)  # seconds; scratch for backward jump stats


class Aligner:
    def __init__(self, ref_features: np.ndarray) -> None:
        self.n_ref = len(ref_features)
        self.pad = max([frames(w) for w in ACQ_WINDOWS] + [frames(TRACK_WINDOW_SECONDS)])
        self.ref = np.concatenate([np.zeros((self.pad, FEATURE_DIM), dtype=np.float32), ref_features.astype(np.float32)])
        self.mode = "acquiring"  # 'acquiring' | 'tracking'
        self._run: list[tuple[int, float]] = []  # consecutive passing candidates: (newest live frame, offset)
        self._offset = 0.0  # tracking: ref frame = live frame + offset

    def _scan_acquisition(self, seconds: float, live: np.ndarray, i_end: int) -> dict | None:
        """Score one acquisition window length; None if not enough live audio yet."""
        w = frames(seconds)
        if i_end + 1 < w:
            return None
        min_score, min_left, min_right = ACQ_WINDOWS[seconds]
        j_hi = min(frames(ACQ_REF_SECONDS), self.n_ref - 1)
        win = live[i_end - w + 1 : i_end + 1]
        scores = window_scores(self.ref, self.pad, win, np.ones(w, dtype=np.float32), 0, j_hi)
        b = int(np.argmax(scores))
        j, best, _ = analyze_peak(scores, b)
        left, right = side_margins(scores, b)
        ok = best >= min_score and left >= min_left and right >= min_right
        return {"seconds": seconds, "ok": ok, "j": j, "left": left, "right": right}

    def _acquire_step(self, live: np.ndarray, i_end: int, result: Result) -> bool:
        """Runs one acquisition-phase update. Returns True if this step locked (switches self.mode to 'tracking')."""
        passing = []
        for s in sorted(ACQ_WINDOWS):
            scan = self._scan_acquisition(s, live, i_end)
            if scan is not None and scan["ok"]:
                passing.append(scan)
        if passing:
            longest = passing[-1]  # sorted ascending, so this is the longest window that passed
            offset = longest["j"] - i_end
            if self._run and abs(offset - self._run[-1][1]) <= AGREE_TOL_FRAMES:
                self._run.append((i_end, offset))
            else:
                self._run = [(i_end, offset)]
        else:
            self._run = []
            return False
        if i_end - self._run[0][0] >= frames(LOCK_AGREE_SECONDS):
            self.mode = "tracking"
            self._offset = self._run[-1][1]
            result.acquisition_time_s = (i_end + 1) * FRAME_SECONDS
            result.acquisition_left_margin = longest["left"]
            result.acquisition_right_margin = longest["right"]
            result.acquisition_window_s = longest["seconds"]
            return True
        return False

    def _track_step(self, live: np.ndarray, i_end: int, result: Result) -> str:
        """Runs one tracking-phase update. Returns 'ok', 'low', or 'beyond_ref' (ref exhausted, caller should stop)."""
        w = min(frames(TRACK_WINDOW_SECONDS), i_end + 1)
        radius = frames(TRACK_RADIUS_SECONDS)
        center = int(round(i_end + self._offset))
        j_lo = max(0, center - radius)
        j_hi = min(self.n_ref - 1, center + radius)
        if j_hi < j_lo:
            return "beyond_ref"
        win = live[i_end - w + 1 : i_end + 1]
        weights = recency_weights(w, TRACK_RECENCY_TIERS)
        scores = window_scores(self.ref, self.pad, win, weights, j_lo, j_hi)

        cur = int(np.clip(center - j_lo, 0, len(scores) - 1))
        cur_score = float(scores[cur])

        # Sticky choice: stay on the current frame unless an adjacent / farther candidate is enough better.
        options = []  # (score, index) of candidates that clear their switch gain
        adjacent = [
            i for d in range(1, TRACK_ADJACENT_FRAMES + 1) for i in (cur - d, cur + d) if 0 <= i < len(scores)
        ]
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

        gain_mask = np.ones(len(scores), dtype=bool)
        gain_mask[max(0, pick - GAIN_EXCLUSION_FRAMES) : pick + GAIN_EXCLUSION_FRAMES + 1] = False
        if gain_mask.any():
            result.gain_samples.append(best - float(scores[gain_mask].max()))

        delta = pick - cur
        if delta > JUMP_THRESHOLD_FRAMES:
            result.forward_jump_samples.append(delta * FRAME_SECONDS)
        elif delta < -JUMP_THRESHOLD_FRAMES:
            result.backward_jump_samples.append(-delta * FRAME_SECONDS)

        result.snapshots.append(TrackSnapshot((i_end + 1) * FRAME_SECONDS, j_lo, scores.copy(), cur, pick))
        result.tracking_steps += 1

        ok = best >= TRACK_MIN_SCORE
        if ok:
            j = i_end + self._offset if pick == cur else j_lo + analyze_peak(scores, pick)[0]
            self._offset = j - i_end
        return "ok" if ok else "low"

    def run(self, live: np.ndarray, max_duration_s: float | None = None) -> Result:
        """Steps through `live` (precomputed live chroma) UPDATE_FRAMES at a time, simulating the online tracker.
        Stops at end of live audio, when the tracking search would run past the end of the ref, after
        TRACK_FAIL_STREAK consecutive low-confidence tracking updates, or -- deliberately, not counted as a failure
        -- once max_duration_s of live audio has been processed (e.g. to cut off audience noise at the end of a
        recording before it drags the tracker down)."""
        result = Result()
        low_streak = 0
        last_i_end = -1
        for i_end in range(UPDATE_FRAMES - 1, len(live), UPDATE_FRAMES):
            if max_duration_s is not None and (i_end + 1) * FRAME_SECONDS > max_duration_s:
                result.stop_reason = "max_duration"
                break
            last_i_end = i_end
            if self.mode == "acquiring":
                self._acquire_step(live, i_end, result)
                continue
            status = self._track_step(live, i_end, result)
            if status == "beyond_ref":
                result.stop_reason = "ref_end"
                last_i_end -= UPDATE_FRAMES  # this update wasn't actually scored
                break
            if status == "ok":
                low_streak = 0
            else:
                if low_streak == 0:
                    result.failed_track_timestamp_s = (i_end + 1) * FRAME_SECONDS
                low_streak += 1
                if low_streak >= TRACK_FAIL_STREAK:
                    result.stop_reason = "track_failed"
                    break
        else:
            result.stop_reason = "live_end"
        result.audio_seconds_processed = (last_i_end + 1) * FRAME_SECONDS if last_i_end >= 0 else 0.0
        if result.gain_samples:
            result.median_gain = float(np.percentile(result.gain_samples, 50))
            result.p25_gain = float(np.percentile(result.gain_samples, 25))
            result.p10_gain = float(np.percentile(result.gain_samples, 10))
            result.p5_gain = float(np.percentile(result.gain_samples, 5))
        result.forward_jump_count = len(result.forward_jump_samples)
        result.backward_jump_count = len(result.backward_jump_samples)
        if result.forward_jump_samples:
            result.avg_forward_jump_s = float(np.mean(result.forward_jump_samples))
            result.farthest_forward_jump_s = float(np.max(result.forward_jump_samples))
        if result.backward_jump_samples:
            result.avg_backward_jump_s = float(np.mean(result.backward_jump_samples))
            result.farthest_backward_jump_s = float(np.max(result.backward_jump_samples))
        return result
