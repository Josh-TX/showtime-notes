"""The one websocket connection per client: device name handshake, broadcast delivery, and (for whichever client is
currently the listener) binary PCM audio frames in. All other mutations go through the REST API in routes_api.py -
this module only owns things tied to a specific connection's identity."""
import json

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from . import listen_service, recording, sync_service, ws_manager
from .audio_buffer import LIVE_PEAKS_PER_SECOND
from .config import AUDIO_HEADER_BYTES
from .state import state

router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        hello_raw = await websocket.receive_text()
        hello = json.loads(hello_raw)
        device_name = (hello.get("payload") or {}).get("deviceName") or "Anonymous"
    except Exception:
        await websocket.close()
        return

    ws_manager.manager.register(websocket, device_name)
    await ws_manager.manager.send_to(websocket, "show_update", state.to_show_info().model_dump(by_alias=True))
    await state.broadcast_show()

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            if message.get("text") is not None:
                await _handle_control_message(websocket, json.loads(message["text"]))
            elif message.get("bytes") is not None:
                await _handle_audio_chunk(websocket, message["bytes"])
    except WebSocketDisconnect:
        pass
    finally:
        was_listener = ws_manager.manager.listener_ws is websocket
        ws_manager.manager.unregister(websocket)
        if was_listener:
            state.listener_device_name = None
        await state.broadcast_show()


async def _handle_control_message(websocket: WebSocket, message: dict) -> None:
    type_ = message.get("type")
    payload = message.get("payload") or {}
    client = ws_manager.manager.clients.get(websocket)
    if client is None:
        return

    if type_ == "become_listener":
        ws_manager.manager.listener_ws = websocket
        state.listener_device_name = client.device_name
        await state.broadcast_show()
    elif type_ == "release_listener":
        if ws_manager.manager.listener_ws is websocket:
            ws_manager.manager.listener_ws = None
            state.listener_device_name = None
            await state.broadcast_show()
    elif type_ == "set_recording_preview_subscription":
        ws_manager.manager.set_recording_preview_wanted(websocket, bool(payload.get("wanted")))
    elif type_ == "set_live_audio_subscription":
        ws_manager.manager.set_live_audio_wanted(websocket, bool(payload.get("wanted")))


async def _handle_audio_chunk(websocket: WebSocket, data: bytes) -> None:
    if ws_manager.manager.listener_ws is not websocket or len(data) <= AUDIO_HEADER_BYTES:
        return
    pcm = np.frombuffer(data[AUDIO_HEADER_BYTES:], dtype="<i2")

    state.rolling_buffer.push(pcm)
    if ws_manager.manager.has_recording_preview_subscribers():
        buf = state.rolling_buffer
        await ws_manager.manager.broadcast_to_recording_preview_subscribers(
            "recording_preview",
            {
                "endTsMs": buf.end_ts_ms,
                "endPeakIndex": buf.end_peak_index,
                "peaksPerSecond": LIVE_PEAKS_PER_SECOND,
                "peaks": buf.peaks(len(pcm)),
            },
        )
    await recording.push_audio(pcm)
    await sync_service.feed_live_audio(pcm)
    await listen_service.handle_chunk(pcm, data)
