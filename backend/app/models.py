from enum import Enum
from typing import Literal

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
    SYNCING = "syncing"  # this song is the sync target; see SyncState.phase for acquiring vs. tracking


NoteColor = Literal[
    "light-red",
    "light-orange",
    "light-yellow",
    "light-green",
    "light-blue",
    "light-purple",
    "light-pink",
    "white",
    "gray",
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "purple",
    "pink",
    "light-gray",
    "dark-gray",
    "dark-red",
    "dark-orange",
    "dark-yellow",
    "dark-green",
    "dark-blue",
    "dark-purple",
    "dark-pink",
    "silver",
    "black",
    "brown",
]


class TimelineNote(ApiModel):
    id: str
    time_seconds: float
    y: float = 0  # px from the timeline top to the note's top edge
    text: str
    color: NoteColor = "gray"


class FavoriteNote(ApiModel):
    id: str
    text: str
    color: NoteColor


class Song(ApiModel):
    id: str
    name: str
    status: SongStatus
    duration_seconds: float | None = None
    free_notes: str = ""
    timeline_notes: list[TimelineNote] = []
    processing_progress: float | None = None  # 0-1, set while status == processing
    processing_message: str | None = None  # what's happening next, set while status == processing
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
    SYNCING = "syncing"


class SyncPhase(str, Enum):
    """Sub-state of SyncStatus.SYNCING: ACQUIRING while searching for a lock, TRACKING once locked on."""

    ACQUIRING = "acquiring"
    TRACKING = "tracking"


class ConfidenceBar(ApiModel):
    """One candidate-position score. While acquiring, a full snapshot spans the whole scan range at fixed
    ref-song coordinates; while tracking, a snapshot spans a small window around the current position estimate."""

    ref_seconds: float
    score: float


class SyncCandidate(ApiModel):
    """One candidate ref-song position considered while acquiring: a local-maximum score peak (indexing into
    the sibling `bars` list) with its exclusion-zone margins to the next-best rival on each side."""

    bar_index: int
    score: float
    left_margin: float
    right_margin: float


class SyncState(ApiModel):
    status: SyncStatus = SyncStatus.NONE
    phase: SyncPhase | None = None  # None iff status is NONE
    target_song_id: str | None = None
    acquire_mode: AcquireMode | None = None
    acquire_lo_seconds: float | None = None  # ref-song scan range while acquiring; kept across drops from tracking
    acquire_hi_seconds: float | None = None
    anchor_ref_seconds: float | None = None  # ref-song time at wallclock_ms; None while acquiring
    wallclock_ms: float | None = None  # when the latest snapshot (anchor + bars) was computed; set in both phases
    bars: list[ConfidenceBar] = []
    best_candidates: list[SyncCandidate] = []  # acquiring only; empty while tracking
    passing_bar_index: int | None = None  # acquiring only; bar whose scan passed the thresholds this step


class ListenerInfo(ApiModel):
    device_name: str | None = None


class ClientInfo(ApiModel):
    device_name: str


class ShowInfo(ApiModel):
    songs: list[SongSummary]
    listener: ListenerInfo
    sync: SyncState
    clients: list[ClientInfo]
    favorites: list[list[FavoriteNote]] = []  # one list per column, top to bottom
