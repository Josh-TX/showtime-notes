from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SONGS_DIR = DATA_DIR / "songs"
SHOW_FILE = DATA_DIR / "show.json"

# -- listener -> server audio transport --
CAPTURE_SR = 48000
CAPTURE_CHUNK_SAMPLES = 960  # 20ms @ 48kHz
CAPTURE_CHUNK_BYTES = CAPTURE_CHUNK_SAMPLES * 2  # int16
AUDIO_HEADER_FORMAT = "<II"  # seq: uint32, timestamp: uint32
AUDIO_HEADER_BYTES = 8

# -- rolling buffer --
ROLLING_BUFFER_SECONDS = 4.0  # recording can start up to 3s back; extra second absorbs click latency

# -- recording --
RECORDING_MAX_SECONDS = 20 * 60

# -- persisted audio --
STORAGE_CODEC = "aac"
STORAGE_BITRATE_KBPS = 96

SONGS_DIR.mkdir(parents=True, exist_ok=True)
