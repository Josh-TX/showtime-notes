import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("SHOWTIME_DATA") or Path(__file__).resolve().parent.parent / "data")
SONGS_DIR = DATA_DIR / "songs"
SHOW_FILE = DATA_DIR / "show.json"

# -- listener -> server audio transport --
CAPTURE_SR = 48000
CAPTURE_CHUNK_SAMPLES = 960  # 20ms @ 48kHz
CAPTURE_CHUNK_BYTES = CAPTURE_CHUNK_SAMPLES * 2  # int16
AUDIO_HEADER_FORMAT = "<II"  # seq: uint32, timestamp: uint32
AUDIO_HEADER_BYTES = 8

# -- rolling buffer --
ROLLING_BUFFER_SECONDS = 13.0  # recording can start up to 12s back; extra second absorbs click latency

# -- recording --
RECORDING_MAX_SECONDS = 20 * 60

# -- persisted audio --
# libsndfile has no direct bitrate setting; for CBR mono this level yields 96 kbps (0 = max bitrate, <1)
STORAGE_MP3_COMPRESSION_LEVEL = 0.78

SONGS_DIR.mkdir(parents=True, exist_ok=True)
