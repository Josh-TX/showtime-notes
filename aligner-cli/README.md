# aligner-cli

Offline, fast-as-possible test harness for tuning the chroma live-aligner. It reimplements the same acquisition +
tracking algorithm as `backend/app/aligner.py` (not imported/referenced — a separate, standalone copy so it can
diverge freely), but takes two audio files instead of a realtime mic stream, and never falls back to "acquiring"
once tracking starts — a run either keeps tracking to the end, or fails and stops.

This is a throwaway experimentation project. Once you land on settings you like, port them back into
`backend/app/aligner.py` and `backend/app/chroma.py` by hand.

## Usage

```
uv run python aligner.py reference.mp3 live.mp3 [--out report_dir] [--image-count 5] [--max-duration 11m15s]
```

`--max-duration` stops processing after that much live audio regardless of what's still ahead (e.g. to cut off
audience noise at the end of a recording before it drags tracking down) — this is a deliberate cutoff, not counted
as a failure. Accepts `11m15s`, `1h2m3s`, `45s`, `11:15`, or a bare number of seconds.

- Prints one JSON object of metrics to stdout.
- Writes up to `--image-count` (default 5) PNG visual reports into the folder `--out` points at (default
  `<live-basename>_report/` in the cwd), named `<i>of<n>_t<seconds>s.png` — each a bar chart of the tracking-window
  candidate scores at one update, same as the realtime UI's confidence bars. The updates are spread evenly across
  the tracked duration (image count 1 picks the midpoint, same as before); fewer than `--image-count` images come
  out if tracking doesn't run long enough to have that many distinct updates. `reportImages` is `[]` if tracking
  never ran at all.
- Accepts anything `ffmpeg` can decode, not just mp3.
- Stops as soon as: the live file runs out, the tracking search would run past the end of the ref, tracking fails
  (see below), or `--max-duration` is hit. Only audio up to "now" is ever considered — nothing downstream of the
  current live position is read.

## Files

- `features.py` — chroma feature extraction (STFT → 12 pitch classes + loudness). All extraction params (SR, FFT
  size, hop, compression, silence ramp, etc.) are constants at the top with tuning comments.
- `tracker.py` — the `Aligner` class: acquisition (initial lock) + tracking. All acquisition/tracking thresholds
  (window lengths, margins, switch gains, fail streak, etc.) are constants at the top with tuning comments.
- `report.py` — the PNG visual reports.
- `aligner.py` — CLI entry point: decode → chroma → run → print JSON → write PNGs.

To tune, edit the constants directly in `features.py` / `tracker.py` and rerun — there's no config file/flags for
them on purpose, so a diff of those two files is the record of what a given experiment changed.

## How it works

Both files' chroma is computed up front in one vectorized batch (fast). This is equivalent to streaming it frame by
frame: each chroma frame only depends on its own ~370ms analysis window, so precomputing the whole file doesn't leak
any future information. The tracker then steps through the live chroma `UPDATE_FRAMES` (10 frames, ~500ms) at a
time, exactly like the realtime version, just without the wall-clock/websocket plumbing.

**Acquisition:** searches the first `ACQ_REF_SECONDS` of the ref with a couple of window lengths (2s, 4s by
default); each needs its own score + left/right margin bar to "pass". A run of agreeing passes for
`LOCK_AGREE_SECONDS` of live audio locks tracking to that offset.

**Tracking:** each update scores ref candidates within `TRACK_RADIUS_SECONDS` of the predicted position and stays
put unless a candidate beats the current position by enough (adjacent vs. jump have separate thresholds). If the
best candidate scores below `TRACK_MIN_SCORE` for `TRACK_FAIL_STREAK` updates in a row, the run ends —
**there is no reverting to "acquiring"; a failure is terminal**, unlike the realtime aligner's verify-rescan
(which this harness deliberately drops).

## Output fields

| Field | Meaning |
|---|---|
| `acquisitionTimeSeconds` | Live-audio seconds elapsed when it locked; `null` if it never locked |
| `acquisitionLeftMargin` / `acquisitionRightMargin` | Margins of the window that triggered the lock |
| `acquisitionWindowSeconds` | Which window length (e.g. `2.0`) triggered the lock |
| `failedTrackTimestampSeconds` | Live-audio seconds at the start of the low-confidence streak that ended the run; `null` if it never happened |
| `stopReason` | `live_end` \| `ref_end` \| `track_failed` \| `max_duration` |
| `trackingSteps` | Number of tracking updates run |
| `medianGain` / `p25Gain` / `p10Gain` / `p5Gain` | Percentiles (50th/25th/10th/5th) of (chosen score − best candidate more than `GAIN_EXCLUSION_FRAMES` away), across all tracking updates; lower percentiles show how bad the worst moments get |
| `forwardJumpCount` / `backwardJumpCount` | Number of tracking updates where the chosen position relocated more than `JUMP_THRESHOLD_FRAMES` forward/backward from the predicted position |
| `avgForwardJumpSeconds` / `avgBackwardJumpSeconds` | Avg relocation distance of those jumps; `null` if the count is 0 |
| `farthestForwardJumpSeconds` / `farthestBackwardJumpSeconds` | Largest relocation distance of those jumps; `null` if the count is 0 |
| `trackingScore` | Single number (nominally ~0-100, uncapped either direction) blending the gain percentiles and jump rate/magnitude, for comparing tuning runs; `0` if tracking failed outright (see `SCORE_*`/`GAIN_SCORE_*` constants in `tracker.py`) |
| `gainScore` / `jumpScore` | The two 0-100 (uncapped) subscores `trackingScore` blends (weighted `SCORE_GAIN_WEIGHT`/`SCORE_JUMP_WEIGHT`); use these to see *why* `trackingScore` moved |
| `audioSecondsProcessed` | Live-audio seconds actually processed before stopping |
| `refDurationSeconds` / `liveDurationSeconds` | Full decoded durations of the two input files |
| `wallSeconds` | Wall-clock time for decode + chroma + the full run (everything except printing/saving output) |
| `realtimeSpeedFactor` | `audioSecondsProcessed / wallSeconds` |
| `reportImages` | Paths to the PNGs, in chronological order; `[]` if tracking never produced any data |

## Setup

```
uv sync
```
