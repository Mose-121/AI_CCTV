"""
streaming_routes.py — WebSocket endpoints for MJPG streaming and UI updates.
"""

import asyncio
import logging
import time

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from service import app_state
from service.auth import TokenClaims, require_user_ws
from service.camera_manager import encode_frame_to_jpeg, is_stale
from service.config import BLACK_480P

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Streaming"])


# ──────────────────────────────────────────────
#  WebSocket: /ws/ui-updates
# ──────────────────────────────────────────────
@router.websocket("/ws/ui-updates")
async def ws_ui_updates(ws: WebSocket):
    await ws.accept()
    app_state.event_subscribers.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            app_state.event_subscribers.remove(ws)
        except Exception:
            pass


# ──────────────────────────────────────────────
#  WebSocket: /ws/mjpg/{camera_name}
# ──────────────────────────────────────────────
@router.websocket("/ws/mjpg/{camera_name}")
async def ws_mjpg(
    ws: WebSocket,
    camera_name: str,
    claims: TokenClaims = Depends(require_user_ws),
):
    if camera_name not in app_state.camera_meta_by_name:
        await ws.close(code=4004, reason=f"Camera {camera_name} not found")
        return

    await ws.accept()
    fps_target = 15
    interval = 1.0 / fps_target
    last_send = 0.0

    try:
        while True:
            now = time.time()
            elapsed = now - last_send

            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)
                continue

            mode = app_state.preview_mode.get(camera_name, "main")
            frame = None

            if mode == "sub":
                with app_state.latest_lock:
                    frame = app_state.latest_frame_sub.get(camera_name)
                if frame is None:
                    with app_state.latest_lock:
                        frame = app_state.latest_frame.get(camera_name)
            else:
                with app_state.latest_lock:
                    frame = app_state.latest_frame.get(camera_name)

            if frame is None or is_stale(camera_name):
                frame = BLACK_480P

            jpg = encode_frame_to_jpeg(frame)
            if jpg:
                try:
                    await ws.send_bytes(jpg)
                    last_send = time.time()
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"[WS MJPG {camera_name}] Error: {e}")
    finally:
        try:
            await ws.close()
        except Exception:
            pass
