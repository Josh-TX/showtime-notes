"""The server-side source of truth: show/song order, song metadata/notes, sync status, listener/client info.
Clients only hold local UI state (selected song, scroll position) - everything here is shared and broadcast on
change."""
from . import storage, ws_manager
from .aligner import LiveAligner
from .audio_buffer import RecordingBuffer, RollingBuffer
from .models import ClientInfo, ListenerInfo, Song, SongStatus, SongSummary, ShowInfo, SyncState


class ServerState:
    def __init__(self) -> None:
        show = storage.load_show()
        self.song_order: list[str] = show["songOrder"]
        self.acquire_start_range_seconds: float = show["acquireStartRangeSeconds"]

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
            self.songs[song_id] = song
        self.persist_show()

        self.rolling_buffer = RollingBuffer()
        self.recording: RecordingBuffer | None = None
        self.recording_pre_roll_included = False
        self.recording_song_id: str | None = None

        self.listener_device_name: str | None = None
        self.sync = SyncState()
        self.live_aligner: LiveAligner | None = None
        self.chroma_stream = None  # ChromaStream | None; created fresh per sync target
        self.chroma_resampler = None  # StreamResampler | None; ditto

    # -- persistence --
    def persist_show(self) -> None:
        storage.save_show(self.song_order, self.acquire_start_range_seconds)

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
