"""Live audio 'listen' feature: an always-on loudness scalar for the navbar meter, plus opt-in full audio relay for
clients that explicitly asked for it. No backpressure handling for a lagging subscriber - rare feature, natural
WS/TCP buffering is fine."""
import numpy as np

from . import ws_manager


FLOOR_DB = -70.0
CEIL_DB = -10.0


async def handle_chunk(samples_int16: np.ndarray, raw_frame: bytes) -> None:
    rms = float(np.sqrt(np.mean(np.square(samples_int16.astype(np.float32))))) / 32768.0
    db = 20.0 * np.log10(rms) if rms > 0 else FLOOR_DB
    level = max(0.0, min(1.0, (db - FLOOR_DB) / (CEIL_DB - FLOOR_DB)))
    await ws_manager.manager.broadcast("loudness", {"level": level})
    await ws_manager.manager.broadcast_binary_to_live_audio_subscribers(raw_frame)
