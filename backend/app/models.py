from enum import Enum

from pydantic import BaseModel, ConfigDict


def _to_camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(w.capitalize() for w in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


class SongStatus(str, Enum):
    RECORDING = "recording"
    PROCESSING = "processing"
    READY = "ready"
    ACQUIRING_SYNC = "acquiring-sync"
    SYNCED = "synced"


class TrackNote(ApiModel):
    id: str
    time_seconds: float
    text: str


class Song(ApiModel):
    id: str
    name: str
    status: SongStatus
    duration_seconds: float | None = None
    free_notes: str = ""
    track_notes: list[TrackNote] = []
    processing_progress: float | None = None  # 0-1, set while status == processing
    processing_error: str | None = None


class SongSummary(ApiModel):
    """Lightweight per-song info for the general show/song-list payload."""

    id: str
    name: str
    status: SongStatus
    duration_seconds: float | None = None


class AcquireMode(str, Enum):
    START = "acquire-sync-start"
    MIDDLE = "acquire-sync-middle"


class SyncStatus(str, Enum):
    NONE = "none"
    ACQUIRING = "acquiring-sync"
    SYNCED = "synced"


class ConfidenceBar(ApiModel):
    ref_seconds: float
    score: float


class SyncState(ApiModel):
    status: SyncStatus = SyncStatus.NONE
    target_song_id: str | None = None
    acquire_mode: AcquireMode | None = None
    anchor_ref_seconds: float | None = None  # ref-song time at anchor_wallclock_ms; None while acquiring
    anchor_wallclock_ms: float | None = None
    bars: list[ConfidenceBar] = []


class ListenerInfo(ApiModel):
    device_name: str | None = None


class ClientInfo(ApiModel):
    device_name: str


class ShowInfo(ApiModel):
    songs: list[SongSummary]
    listener: ListenerInfo
    sync: SyncState
    clients: list[ClientInfo]
