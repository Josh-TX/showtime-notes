"""Visual report: bar charts of the tracking-window candidate scores (the same "confidence bars" the realtime UI
shows), taken from a handful of tracking updates spread across the live audio actually processed."""
from pathlib import Path

from features import frame_center_seconds
from tracker import Result, TrackSnapshot


def _pick_snapshots(result: Result, count: int) -> list[TrackSnapshot]:
    """Up to `count` snapshots spread evenly across the tracked duration (count=1 picks the midpoint, same as
    before). Fewer than `count` come back if there aren't enough distinct tracking updates (e.g. tracking failed
    quickly) -- duplicate picks collapse rather than padding out the list."""
    if not result.snapshots or count <= 0:
        return []
    total = result.audio_seconds_processed
    targets = [(i + 1) / (count + 1) * total for i in range(count)]
    picked, seen = [], set()
    for t in targets:
        snap = min(result.snapshots, key=lambda s: abs(s.live_s - t))
        if id(snap) not in seen:
            seen.add(id(snap))
            picked.append(snap)
    picked.sort(key=lambda s: s.live_s)
    return picked


def _plot(snap: TrackSnapshot, result: Result, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs = [frame_center_seconds(snap.j_lo + i) for i in range(len(snap.scores))]
    colors = ["#888888"] * len(snap.scores)
    colors[snap.cur_idx] = "#3b82f6"  # predicted position going into this update
    colors[snap.pick_idx] = "#22c55e"  # chosen position after this update

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(xs, snap.scores, width=(xs[1] - xs[0]) if len(xs) > 1 else 0.05, color=colors)
    ax.set_xlabel("ref position (s)")
    ax.set_ylabel("score")
    ax.set_title(
        f"tracking window at live={snap.live_s:.1f}s (of {result.audio_seconds_processed:.1f}s processed)\n"
        "blue = predicted position, green = chosen position"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def write_report(result: Result, out_dir: str, image_count: int = 5) -> list[str]:
    """Writes up to `image_count` PNGs into out_dir (created if missing), named `<i>of<n>_t<seconds>s.png`, and
    returns their paths in chronological order (empty list, nothing written, if tracking never produced any
    snapshots)."""
    picked = _pick_snapshots(result, image_count)
    if not picked:
        return []
    dir_path = Path(out_dir)
    dir_path.mkdir(parents=True, exist_ok=True)
    written = []
    for i, snap in enumerate(picked, start=1):
        path = dir_path / f"{i}of{len(picked)}_t{snap.live_s:.1f}s.png"
        _plot(snap, result, path)
        written.append(str(path))
    return written
