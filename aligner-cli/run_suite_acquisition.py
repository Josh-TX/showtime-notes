#!/usr/bin/env python3
"""Runs aligner.py on every case in ../media and compares acquisitionTimeSeconds against a hardcoded
per-case floor: the earliest the current algorithm could possibly lock for that case, given (a) how much
real (non-silent) audio the ref/live files actually have at their start and (b) the algorithm's fixed
structural minimum of ACQUIRE_WINDOW_SECONDS + LOCK_AGREE_SECONDS (~5.0s) before a lock can ever fire.

This is separate from run_suite.py (which tracks gainScore/jumpScore/trackingScore, i.e. tracking-phase
quality) -- this one is only about how quickly and correctly acquisition locks.

Floors below were derived by measuring sustained chroma-presence onset in both the ref and live file of
each case (first point where presence stays > 0.3 for 10 consecutive frames): all 5 current corpus cases
have onset well under 1s, so none of them have a lead-in long enough to push the floor past the ~5.0s
structural minimum. If a case is added with a genuine multi-second silent lead-in (recording started
early, quiet intro, etc.), its floor here should be raised to (onset + ACQUIRE_WINDOW_SECONDS +
LOCK_AGREE_SECONDS) -- re-derive with the onset probe below rather than guessing:

    uv run python - <<'EOF'
    import numpy as np
    from pathlib import Path
    from features import compute_chroma, decode_audio
    from tracker import FRAME_SECONDS
    for p in [Path("../media/<case>/ref - x.opus"), Path("../media/<case>/live - y.opus")]:
        presence = np.linalg.norm(compute_chroma(decode_audio(p)), axis=1)
        onset = next((i for i in range(len(presence) - 10) if np.all(presence[i:i+10] > 0.3)), None)
        print(p.name, onset * FRAME_SECONDS if onset is not None else None)
    EOF

Usage: uv run python run_suite_acquisition.py [aligner.py args passed through]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

MEDIA_DIR = Path(__file__).resolve().parent.parent / "media"
ALIGNER = Path(__file__).resolve().parent / "aligner.py"

# case name -> earliest possible acquisitionTimeSeconds (see module docstring for how these were derived)
EXPECTED_FLOOR_SECONDS = {
    "hallelujah chorus": 5.0,
    "moonlight": 5.0,
    "newworld": 5.0,
    "prince denmark": 5.0,
    "russia": 5.0,
}


def find_case(folder: Path) -> tuple[Path, Path]:
    live = next(folder.glob("live*"), None)
    ref = next(folder.glob("ref*"), None)
    if live is None or ref is None:
        raise SystemExit(f"{folder}: missing live/ref file")
    return ref, live


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    args, passthrough = parser.parse_known_args()

    cases = sorted(p for p in MEDIA_DIR.iterdir() if p.is_dir())
    missing = [c.name for c in cases if c.name not in EXPECTED_FLOOR_SECONDS]
    if missing:
        print(f"warning: no expected floor hardcoded for: {', '.join(missing)}", file=sys.stderr)

    rows = []
    for case in cases:
        ref, live = find_case(case)
        proc = subprocess.run(
            [sys.executable, str(ALIGNER), str(ref), str(live), "--image-count", "0", *passthrough],
            capture_output=True, text=True, cwd=ALIGNER.parent,
        )
        if proc.returncode != 0:
            print(f"{case.name}: FAILED\n{proc.stderr}", file=sys.stderr)
            continue
        data = json.loads(proc.stdout)
        floor = EXPECTED_FLOOR_SECONDS.get(case.name)
        actual = data["acquisitionTimeSeconds"]
        delay = None if (actual is None or floor is None) else round(actual - floor, 3)
        rows.append((case.name, floor, actual, delay, data["acquisitionLeftMargin"], data["acquisitionRightMargin"], data["stopReason"]))

    name_w = max(len("case"), *(len(r[0]) for r in rows)) if rows else len("case")
    header = f"{'case':<{name_w}}  {'floor':>6}  {'actual':>7}  {'delay':>7}  {'left':>6}  {'right':>6}  stopReason"
    print(header)
    print("-" * len(header))
    for name, floor, actual, delay, left, right, stop in rows:
        floor_s = f"{floor:.1f}" if floor is not None else "?"
        actual_s = f"{actual:.2f}" if actual is not None else "NEVER"
        delay_s = f"{delay:+.2f}" if delay is not None else "-"
        left_s = f"{left:.3f}" if left is not None else "-"
        right_s = f"{right:.3f}" if right is not None else "-"
        print(f"{name:<{name_w}}  {floor_s:>6}  {actual_s:>7}  {delay_s:>7}  {left_s:>6}  {right_s:>6}  {stop}")

    delays = [r for r in rows if r[3] is not None]
    if delays:
        print("-" * len(header))
        avg = sum(r[3] for r in delays) / len(delays)
        worst = max(delays, key=lambda r: r[3])
        print(f"avg delay over floor: {avg:+.2f}s   worst: {worst[3]:+.2f}s ({worst[0]})")


if __name__ == "__main__":
    main()
