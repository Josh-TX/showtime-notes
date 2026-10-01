"""The server-side source of truth: show/song order, song metadata/notes, sync status, listener/client info.
Clients only hold local UI state (selected song, scroll position) - everything here is shared and broadcast on
change."""
from . import storage, ws_manager
from .aligner import LiveAligner
from .audio_buffer import RecordingBuffer, RollingBuffer
from .models import ClientInfo, ListenerInfo, RecentNote, Song, SongStatus, SongSummary, ShowInfo, SyncState


class ServerState:
    def __init__(self) -> None:
        show = storage.load_show()
        self.song_order: list[str] = show["songOrder"]
        self.acquire_start_range_seconds: float = show["acquireStartRangeSeconds"]

        self.recent_notes: list[RecentNote] = [RecentNote.model_validate(r) for r in show.get("recentNotes", [])]

        self.songs: dict[str, Song] = {}
        for song_id in list(self.song_order):
            try:
                song = storage.load_song_meta(song_id)
            except FileNotFoundError:
                self.song_order.remove(song_id)
                continue
            if song.status == SongStatus.RECORDING:
                # the in-progress audio buffer was in-memory only and didn't survive the restart
                self.song_order.remove(song_id)
                storage.delete_song(song_id)
                continue
            if song.status == SongStatus.SYNCING:
                # SyncState isn't persisted, so no song can actually be syncing after a restart
                song.status = SongStatus.READY
            self.songs[song_id] = song
        self.persist_show()

        self.rolling_buffer = RollingBuffer()
        self.recording: RecordingBuffer | None = None
        self.recording_song_id: str | None = None

        self.listener_device_name: str | None = None
        self.sync = SyncState()
        self.live_aligner: LiveAligner | None = None
        self.chroma_stream = None  # ChromaStream | None; created fresh per sync target
        self.chroma_resampler = None  # StreamResampler | None; ditto

    # -- persistence --
    def persist_show(self) -> None:
        storage.save_show(
            self.song_order,
            self.acquire_start_range_seconds,
            [r.model_dump() for r in self.recent_notes],
        )

    # -- read helpers --
    def to_show_info(self) -> ShowInfo:
        return ShowInfo(
            songs=[
                SongSummary(id=s.id, name=s.name, status=s.status, duration_seconds=s.duration_seconds)
                for s in (self.songs[sid] for sid in self.song_order)
            ],
            listener=ListenerInfo(device_name=self.listener_device_name),
            sync=self.sync,
            clients=[ClientInfo(device_name=n) for n in ws_manager.manager.device_names()],
            recent_notes=self.recent_notes,
        )

    # -- mutation + broadcast --
    async def broadcast_show(self) -> None:
        await ws_manager.manager.broadcast("show_update", self.to_show_info().model_dump(by_alias=True))

    async def broadcast_song(self, song_id: str) -> None:
        song = self.songs[song_id]
        await ws_manager.manager.broadcast("song_update", song.model_dump(by_alias=True))

    async def save_and_broadcast_song(self, song: Song) -> None:
        self.songs[song.id] = song
        storage.save_song_meta(song)
        await self.broadcast_song(song.id)


state = ServerState()
