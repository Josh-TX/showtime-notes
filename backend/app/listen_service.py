"""Live audio 'listen' feature: an always-on loudness scalar for the navbar meter, plus opt-in full audio relay for
clients that explicitly asked for it. No backpressure handling for a lagging subscriber - rare feature, natural
WS/TCP buffering is fine."""
import numpy as np

from . import ws_manager
from .audio_buffer import level_from_samples


async def handle_chunk(samples_int16: np.ndarray, raw_frame: bytes) -> None:
    await ws_manager.manager.broadcast("loudness", {"level": level_from_samples(samples_int16)})
    await ws_manager.manager.broadcast_binary_to_live_audio_subscribers(raw_frame)
