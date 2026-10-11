"""Live audio 'listen' feature: an always-on loudness scalar for the navbar meter, plus opt-in full audio relay for
clients that explicitly asked for it. No backpressure handling for a lagging subscriber - rare feature, natural
WS/TCP buffering is fine."""
from collections import deque

import numpy as np

from . import ws_manager
from .audio_buffer import level_from_samples


CLIP_SAMPLE_THRESHOLD = 32700
CLIP_WINDOW_CHUNKS = 10  # 200ms of 20ms chunks
CLIP_WARN_COUNT = 25  # orange (clip level 1)
CLIP_BAD_COUNT = 200  # red (clip level 2)
_recent_clip_counts: deque[int] = deque(maxlen=CLIP_WINDOW_CHUNKS)


async def handle_chunk(samples_int16: np.ndarray, raw_frame: bytes) -> None:
    _recent_clip_counts.append(int(np.count_nonzero(np.abs(samples_int16.astype(np.int32)) >= CLIP_SAMPLE_THRESHOLD)))
    recent_clips = sum(_recent_clip_counts)
    clip_level = 2 if recent_clips > CLIP_BAD_COUNT else 1 if recent_clips >= CLIP_WARN_COUNT else 0
    await ws_manager.manager.broadcast("loudness", {"level": level_from_samples(samples_int16), "clipLevel": clip_level})
    await ws_manager.manager.broadcast_binary_to_live_audio_subscribers(raw_frame)
