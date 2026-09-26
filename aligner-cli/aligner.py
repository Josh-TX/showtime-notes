#!/usr/bin/env python3
"""Offline aligner CLI: scores how well tracker.Aligner acquires and tracks live.mp3 against reference.mp3.

Usage: python aligner.py reference.mp3 live.mp3 [--out report.png] [--image-count 5]

Prints a single JSON object of metrics to stdout. Writes up to --image-count PNG visual reports (tracking-window
confidence bars, spread across the audio processed) unless tracking never produced any data.
"""
import argparse
import json
import re
import time
from pathlib import Path

from features import SR, compute_chroma, decode_audio
from report import write_report
from tracker import Aligner, tracking_score

_DURATION_RE = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?$")


def parse_duration(s: str) -> float:
    """'11m15s' / '1h2m3s' / '45s' / '11:15' / '675' (bare seconds) -> seconds."""
    s = s.strip()
    if ":" in s:
        secs = 0.0
        for part in s.split(":"):
            secs = secs * 60 + float(part)
        return secs
    m = _DURATION_RE.fullmatch(s)
    if m and any(m.groups()):
        h, mnt, sec = m.groups()
        return int(h or 0) * 3600 + int(mnt or 0) * 60 + float(sec or 0)
    return float(s)


def _r(x: float | None, nd: int = 3) -> float | None:
    return None if x is None else round(x, nd)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", help="reference audio file (e.g. reference.mp3)")
    parser.add_argument("live", help="live audio file (e.g. live.mp3)")
    parser.add_argument(
        "--out", default=None,
        help="subfolder name under aligner-cli/images/ for report images (default: <live-basename>_report)",
    )
    parser.add_argument(
        "--max-duration", type=parse_duration, default=None,
        help="stop after this much live audio (e.g. 11m15s, 1h2m3s, 675, 11:15); not counted as a failure",
    )
    parser.add_argument(
        "--image-count", type=int, default=5,
        help="number of report images, spread across the tracked duration (fewer if tracking ends early)",
    )
    args = parser.parse_args()

    start = time.perf_counter()

    ref_audio = decode_audio(Path(args.reference))
    live_audio = decode_audio(Path(args.live))
    ref_features = compute_chroma(ref_audio)
    live_features = compute_chroma(live_audio)

    result = Aligner(ref_features).run(live_features, max_duration_s=args.max_duration)
    score = tracking_score(result)

    wall_seconds = time.perf_counter() - start  # everything above, i.e. everything but emitting output below

    out_name = args.out or f"{Path(args.live).stem}_report"
    out_dir = Path(__file__).resolve().parent / "images" / out_name
    report_images = write_report(result, out_dir, image_count=args.image_count)

    print(json.dumps({
        "acquisitionTimeSeconds": _r(result.acquisition_time_s),
        "acquisitionLeftMargin": _r(result.acquisition_left_margin),
        "acquisitionRightMargin": _r(result.acquisition_right_margin),
        "acquisitionWindowSeconds": result.acquisition_window_s,
        "failedTrackTimestampSeconds": _r(result.failed_track_timestamp_s),
        "stopReason": result.stop_reason,
        "trackingSteps": result.tracking_steps,
        "medianGain": _r(result.median_gain),
        "p25Gain": _r(result.p25_gain),
        "p10Gain": _r(result.p10_gain),
        "p5Gain": _r(result.p5_gain),
        "forwardJumpCount": result.forward_jump_count,
        "backwardJumpCount": result.backward_jump_count,
        "avgForwardJumpSeconds": _r(result.avg_forward_jump_s),
        "avgBackwardJumpSeconds": _r(result.avg_backward_jump_s),
        "farthestForwardJumpSeconds": _r(result.farthest_forward_jump_s),
        "farthestBackwardJumpSeconds": _r(result.farthest_backward_jump_s),
        "trackingScore": _r(score.total, 1),
        "gainScore": _r(score.gain, 1),
        "jumpScore": _r(score.jump, 1),
        "audioSecondsProcessed": _r(result.audio_seconds_processed, 2),
        "refDurationSeconds": _r(len(ref_audio) / SR, 2),
        "liveDurationSeconds": _r(len(live_audio) / SR, 2),
        "wallSeconds": _r(wall_seconds),
        "realtimeSpeedFactor": _r(result.audio_seconds_processed / wall_seconds, 1) if wall_seconds > 0 else None,
        "reportImages": report_images,
    }, indent=2))


if __name__ == "__main__":
    main()
