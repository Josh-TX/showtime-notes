#!/usr/bin/env python3
"""Runs aligner.py on every case in ../media (each subfolder has one `live - *` and one `ref - *` file) and prints
a table of gainScore / jumpScore / trackingScore per case, plus the average row.

Usage: uv run python run_suite.py [--image-count 0] [aligner.py args passed through]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

MEDIA_DIR = Path(__file__).resolve().parent.parent / "media"
ALIGNER = Path(__file__).resolve().parent / "aligner.py"


def find_case(folder: Path) -> tuple[Path, Path]:
    live = next(folder.glob("live*"), None)
    ref = next(folder.glob("ref*"), None)
    if live is None or ref is None:
        raise SystemExit(f"{folder}: missing live/ref file")
    return ref, live


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-count", type=int, default=0, help="passed through to aligner.py (default 0: skip PNGs)")
    args, passthrough = parser.parse_known_args()

    cases = sorted(p for p in MEDIA_DIR.iterdir() if p.is_dir())
    rows = []
    for case in cases:
        ref, live = find_case(case)
        proc = subprocess.run(
            [sys.executable, str(ALIGNER), str(ref), str(live), "--image-count", str(args.image_count), *passthrough],
            capture_output=True, text=True, cwd=ALIGNER.parent,
        )
        if proc.returncode != 0:
            print(f"{case.name}: FAILED\n{proc.stderr}", file=sys.stderr)
            continue
        data = json.loads(proc.stdout)
        rows.append((case.name, data["gainScore"], data["jumpScore"], data["trackingScore"]))

    name_w = max(len("case"), *(len(r[0]) for r in rows)) if rows else len("case")
    header = f"{'case':<{name_w}}  {'gain':>8}  {'jump':>8}  {'total':>8}"
    print(header)
    print("-" * len(header))
    for name, gain, jump, total in rows:
        print(f"{name:<{name_w}}  {gain:>8.1f}  {jump:>8.1f}  {total:>8.1f}")
    if rows:
        n = len(rows)
        avg_gain = sum(r[1] for r in rows) / n
        avg_jump = sum(r[2] for r in rows) / n
        avg_total = sum(r[3] for r in rows) / n
        print("-" * len(header))
        print(f"{'avg':<{name_w}}  {avg_gain:>8.1f}  {avg_jump:>8.1f}  {avg_total:>8.1f}")


if __name__ == "__main__":
    main()
