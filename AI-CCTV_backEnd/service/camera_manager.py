"""
camera_manager.py — Camera spawning, frame pump, sub-preview, health monitor, and helpers.
"""

import asyncio
import datetime as dt
import json
import logging
import os
import queue as qmod
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import cv2
import numpy as np

from service import app_state, utils
from service.car_camera_worker import CarCameraWorker
from service.config import (
    BLACK_480P,
    HEALTH_CHECK_INTERVAL_SEC,
    JPEG_OPTIMIZE,
    JPEG_QUALITY,
    MAX_JPEG_SIDE,
    RECORD_ROOT,
    STALE_SEC,
    TZ,
)
from service.face_camera_worker import FaceCameraWorker
from service.record import VideoRecorder

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────
def norm_zone(z: Optional[str]) -> Optional[str]:
    if not z:
        return None
    s = str(z).strip().lower()
    if s in ("building", "face", "people", "person"):
        return "face"
    if s in ("vehicle", "vehicles", "car"):
        return "car"
    return s


def infer_sub_url_from_main(main_url: str) -> Optional[str]:
    if not main_url:
        return None
    try:
        u = urlparse(main_url)
        qs = dict(parse_qsl(u.query))
        if "subtype" in qs:
            qs["subtype"] = "1"
            return urlunparse(
                (u.scheme, u.netloc, u.path, u.params, urlencode(qs), u.fragment)
            )
        if "/Streaming/Channels/" in u.path:
            tail = u.path.split("/Streaming/Channels/")[-1]
            if tail and tail.isdigit() and len(tail) == 3 and tail.endswith("1"):
                new_tail = tail[:-1] + "2"
                new_path = u.path[:-3] + new_tail
                return urlunparse(
                    (u.scheme, u.netloc, new_path, u.params, u.query, u.fragment)
                )
    except Exception:
        pass
    return None


def even_pad(frame: np.ndarray) -> np.ndarray:
    h, w = frame.shape[:2]
    pad_bottom = h & 1
    pad_right = w & 1
    if pad_bottom or pad_right:
        frame = cv2.copyMakeBorder(
            frame, 0, pad_bottom, 0, pad_right, cv2.BORDER_REPLICATE
        )
    return frame


def open_rtsp(url: str):
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    except Exception:
        pass
    return cap


def encode_frame_to_jpeg(frame: np.ndarray) -> bytes:
    try:
        if frame is None or not hasattr(frame, "shape") or len(frame.shape) != 3:
            frame = np.zeros((360, 640, 3), dtype=np.uint8)
        h, w = frame.shape[:2]
        side = max(h, w)
        if side > MAX_JPEG_SIDE:
            scale = MAX_JPEG_SIDE / float(side)
            frame = cv2.resize(
                frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
            )
        params = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
        if JPEG_OPTIMIZE:
            params += [cv2.IMWRITE_JPEG_OPTIMIZE, 1]
        ok, buf = cv2.imencode(".jpg", frame, params)
        if not ok:
            return b""
        return buf.tobytes()
    except Exception as e:
        logger.error(f"[MJPG] Error encoding frame: {e}")
        return b""


def is_stale(cam: str) -> bool:
    ts = app_state.latest_frame_ts.get(cam, 0.0)
    return (time.time() - ts) > STALE_SEC if ts else True


def has_access_to_camera(camera_name: str, claims) -> bool:
    """Check if the user has access to a specific camera."""
    meta = app_state.camera_meta_by_name.get(camera_name)
    if not meta:
        return False
    cam_comp = meta.get("comp")
    if claims.is_admin:
        return True
    return cam_comp and cam_comp in (claims.access or [])


# ──────────────────────────────────────────────
#  WebSocket broadcast
# ──────────────────────────────────────────────
async def ws_broadcast(event: Dict[str, Any]):
    bad = []
    for ws in list(app_state.event_subscribers):
        try:
            await ws.send_text(json.dumps(event, ensure_ascii=False))
        except Exception:
            bad.append(ws)
    for ws in bad:
        try:
            app_state.event_subscribers.remove(ws)
        except Exception:
            pass


# ──────────────────────────────────────────────
#  Hot-reload known faces into workers
# ──────────────────────────────────────────────
def _l2norm_np(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=-1, keepdims=True) + 1e-9
    return (x / n).astype(np.float32)


def refresh_all_face_workers() -> int:
    refreshed = 0
    for w, *_rest in app_state.workers:
        if not isinstance(w, FaceCameraWorker):
            continue
        try:
            if hasattr(w, "reload_known_faces") and callable(w.reload_known_faces):
                w.reload_known_faces()
                refreshed += 1
                continue
            if w.db is None:
                continue
            known = w.db.load_known_faces()
            with w._kn_lock:
                w.known_ids = [r[0] for r in known]
                w.known_names = [r[2] for r in known]
                w.known_depts = [(r[3] or "Unknown") for r in known]
                if known:
                    embs = np.stack([r[1] for r in known]).astype(np.float32)
                    w.known_embs = _l2norm_np(embs)
                else:
                    w.known_embs = np.empty((0, 512), dtype=np.float32)
            refreshed += 1
            logger.info(f"[ENROLL] Hot-reloaded {len(known)} known faces into worker {w.name}")
        except Exception as e:
            logger.error(f"[ENROLL] refresh worker {getattr(w, 'name', '?')} failed: {e}")
    return refreshed


# ──────────────────────────────────────────────
#  Frame pump — receives frames from worker and stores them
# ──────────────────────────────────────────────
def start_frame_pump(camera_name: str, frame_q: qmod.Queue, recorder: VideoRecorder):
    last_ok_ts = time.time()
    while True:
        try:
            data = frame_q.get(timeout=1.0)
            while True:
                try:
                    data = frame_q.get_nowait()
                except qmod.Empty:
                    break

            if not isinstance(data, tuple) or len(data) < 2:
                continue

            cam_name, frame = data[0], data[1]
            if not hasattr(frame, "shape"):
                continue

            frame2 = even_pad(frame)

            with app_state.latest_lock:
                app_state.latest_frame[cam_name] = frame2
                app_state.latest_frame_ts[cam_name] = time.time()

            try:
                recorder.write_frame(frame2)
            except Exception as e:
                logger.warning(f"[REC {cam_name}] write_frame failed: {e}")

            if os.getenv("PREVIEW_ENHANCE", "1") == "1":
                try:
                    preview_frame = utils.enhance_preview(frame2)
                    with app_state.latest_lock:
                        app_state.latest_frame[cam_name] = preview_frame
                        app_state.latest_frame_ts[cam_name] = time.time()
                except Exception as e:
                    logger.debug(f"[PREVIEW {cam_name}] enhance failed: {e}")

            last_ok_ts = time.time()

        except qmod.Empty:
            if time.time() - last_ok_ts > STALE_SEC:
                with app_state.latest_lock:
                    app_state.latest_frame.pop(camera_name, None)
                    app_state.latest_frame_ts.pop(camera_name, None)
            continue
        except Exception as e:
            logger.error(f"[ERROR] Frame pump {camera_name} error: {e}")
            time.sleep(0.02)


# ──────────────────────────────────────────────
#  Spawn a camera worker + recorder
# ──────────────────────────────────────────────
def spawn_camera(cam: dict) -> bool:
    camera_name = str(cam["camera_name"])
    zone = norm_zone(cam.get("zone")) or "face"
    url = cam["url"]
    comp = cam.get("comp")

    for w, *_rest in app_state.workers:
        if getattr(w, "name", None) == camera_name:
            logger.info(f"[SPAWN] Camera {camera_name} already running")
            return False

    frame_q = qmod.Queue(maxsize=3000)
    log_q = qmod.Queue()
    status_q = qmod.Queue()
    worker = None
    recorder = None

    try:
        if zone == "car":
            logger.info(f"🚗 [SPAWN CAR {camera_name}] URL: {url}")
            worker = CarCameraWorker(
                id=cam.get("id"), name=camera_name, url=url,
                zone=zone, department=comp, user_access=[comp] if comp else [],
            )
        else:
            logger.info(f"👤 [SPAWN FACE {camera_name}] URL: {url}")
            worker = FaceCameraWorker(
                id=cam.get("id"), name=camera_name, camera_url=url,
                zone=zone, department=comp, user_access=[comp] if comp else [],
            )

        with app_state.runtime_settings_lock:
            seg_min = app_state.runtime_settings.get("SEGMENT_MINUTES", 15)

        recorder = VideoRecorder(
            output_dir=RECORD_ROOT, zone=zone,
            segment_minutes=seg_min,
            department=comp or "Unknown", camera_id=camera_name,
        )

        test_cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if not test_cap.isOpened():
            logger.error(f"❌ [SPAWN {camera_name}] URL INVALID: {url}")
            test_cap.release()
            return False
        test_cap.release()
        logger.info(f"✅ [SPAWN {camera_name}] URL OK")

        recorder.start_recording(camera_id=camera_name)
        logger.info(f"📹 [REC {camera_name}] START {comp}/{zone}")

    except Exception as e:
        logger.error(f"❌ [SPAWN {camera_name}] Setup FAILED: {e}")
        if recorder:
            try:
                recorder.stop_recording()
            except Exception:
                pass
        return False

    loop = asyncio.get_running_loop()

    def worker_runner():
        try:
            worker.run(frame_q, log_q, status_q)
        except Exception as e:
            loop.create_task(
                ws_broadcast({"type": "error", "name": camera_name, "message": str(e)})
            )

    def pump():
        while True:
            try:
                try:
                    msg = log_q.get_nowait()
                    loop.create_task(
                        ws_broadcast({"type": "log", "name": camera_name, "message": msg})
                    )
                except qmod.Empty:
                    pass
                try:
                    st = status_q.get_nowait()
                    loop.create_task(
                        ws_broadcast({"type": "status", "name": camera_name, "status": st})
                    )
                except qmod.Empty:
                    pass
                time.sleep(0.05)
            except Exception:
                time.sleep(0.1)

    t_worker = threading.Thread(target=worker_runner, daemon=True)
    t_worker.start()
    threading.Thread(target=pump, daemon=True).start()
    threading.Thread(
        target=start_frame_pump, args=(camera_name, frame_q, recorder), daemon=True
    ).start()

    app_state.workers.append((worker, t_worker, frame_q, log_q, status_q, recorder))
    app_state.camera_meta_by_name[camera_name] = {
        "zone": zone, "url": url, "url2": cam.get("url2"), "comp": comp,
    }
    app_state.preview_mode[camera_name] = "main"

    logger.info(f"✅ [SPAWN {camera_name}] OK | Type: {zone} | Comp: {comp}")
    return True


# ──────────────────────────────────────────────
#  Sub-preview streams
# ──────────────────────────────────────────────
def start_sub_preview(camera_name: str, sub_url: str):
    if camera_name in app_state.sub_preview_threads:
        return
    stop_event = threading.Event()

    def _runner():
        utils.ensure_opencv_rtsp_env()
        cap = None
        last_open = 0.0
        while not stop_event.is_set():
            try:
                if cap is None or not cap.isOpened():
                    if time.time() - last_open < 1.0:
                        time.sleep(0.2)
                        continue
                    cap = open_rtsp(sub_url)
                    last_open = time.time()
                    if not cap or not cap.isOpened():
                        time.sleep(0.5)
                        continue
                ok, frame = cap.read()
                if not ok or frame is None:
                    time.sleep(0.01)
                    try:
                        cap.release()
                    except Exception:
                        pass
                    cap = None
                    continue
                frame2 = even_pad(frame)
                with app_state.latest_lock:
                    app_state.latest_frame_sub[camera_name] = frame2
                time.sleep(0.005)
            except Exception as e:
                logger.error(f"[ERROR] Sub preview {camera_name}: {e}")
                try:
                    if cap:
                        cap.release()
                except Exception:
                    pass
                cap = None
                time.sleep(0.5)
        try:
            if cap:
                cap.release()
        except Exception:
            pass

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    app_state.sub_preview_threads[camera_name] = (t, stop_event)
    logger.info(f"[SUB_PREVIEW {camera_name}] Started for {sub_url}")


def stop_sub_preview(camera_name: str):
    item = app_state.sub_preview_threads.pop(camera_name, None)
    if not item:
        return
    t, stop_event = item
    try:
        stop_event.set()
        t.join(timeout=2.0)
    except Exception:
        pass
    with app_state.latest_lock:
        app_state.latest_frame_sub.pop(camera_name, None)
    logger.info(f"[SUB_PREVIEW {camera_name}] Stopped")


# ──────────────────────────────────────────────
#  Health monitor thread
# ──────────────────────────────────────────────
def generate_health_status() -> dict:
    all_names = list(app_state.camera_meta_by_name.keys())
    down_list = [n for n in all_names if is_stale(n)]
    ok_list = [n for n in all_names if not is_stale(n)]
    return {
        "total": len(all_names),
        "ok_count": len(ok_list),
        "down_count": len(down_list),
        "down_list": down_list,
    }


def camera_health_monitor_thread(loop: asyncio.AbstractEventLoop):
    time.sleep(15)
    logger.info(f"[Health Monitor] Thread started. Interval: {HEALTH_CHECK_INTERVAL_SEC}s")

    try:
        if app_state.db:
            app_state.camera_last_known_status = app_state.db.get_all_last_camera_statuses()
            logger.info(
                f"[Health Monitor] Loaded {len(app_state.camera_last_known_status)} statuses from DB."
            )
    except Exception as e:
        logger.error(f"[Health Monitor] Failed to load last statuses: {e}")

    while True:
        try:
            current_list = list(app_state.camera_meta_by_name.keys())
            now_ts = time.time()

            for cam_name in current_list:
                new_status = "DOWN" if is_stale(cam_name) else "OK"

                with app_state.health_monitor_lock:
                    old_status = app_state.camera_last_known_status.get(cam_name)

                if new_status == "OK":
                    app_state.camera_down_timestamp.pop(cam_name, None)
                    if old_status == "DOWN":
                        logger.warning(f"[Health Monitor] {cam_name} DOWN -> OK")
                        if app_state.db:
                            app_state.db.log_camera_event(cam_name, "OK", dt.datetime.now(TZ))
                    with app_state.health_monitor_lock:
                        app_state.camera_last_known_status[cam_name] = "OK"
                else:
                    if old_status != "DOWN":
                        logger.warning(f"[Health Monitor] {cam_name} OK -> DOWN")
                        app_state.camera_down_timestamp[cam_name] = now_ts
                        with app_state.health_monitor_lock:
                            app_state.camera_last_known_status[cam_name] = "DOWN"
                    else:
                        first_down = app_state.camera_down_timestamp.get(cam_name)
                        if first_down and (now_ts - first_down) >= 1800:
                            logger.error(f"[Health Monitor] {cam_name} DOWN for 30 min. LOGGING.")
                            if app_state.db:
                                app_state.db.log_camera_event(cam_name, "DOWN", dt.datetime.now(TZ))
                            app_state.camera_down_timestamp.pop(cam_name, None)

            with app_state.health_monitor_lock:
                current_statuses = dict(app_state.camera_last_known_status)
            loop.create_task(
                ws_broadcast({"type": "health_status", "data": current_statuses})
            )

        except Exception as e:
            logger.error(f"[Health Monitor] Error in loop: {e}", exc_info=True)

        time.sleep(HEALTH_CHECK_INTERVAL_SEC)


# ──────────────────────────────────────────────
#  Persistent settings
# ──────────────────────────────────────────────
def save_persistent_settings():
    import json as _json

    from service.config import SETTINGS_FILE

    with app_state.runtime_settings_lock:
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                _json.dump(app_state.runtime_settings, f, indent=2)
            logger.info(f"Saved persistent settings to {SETTINGS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save persistent settings: {e}")


def load_persistent_settings():
    import json as _json

    from service.config import SETTINGS_FILE

    default_seg = int(os.getenv("SEGMENT_MINUTES", "15"))
    settings = {"SEGMENT_MINUTES": default_seg}

    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = _json.load(f)
            if "SEGMENT_MINUTES" in data:
                settings["SEGMENT_MINUTES"] = int(data["SEGMENT_MINUTES"])
            logger.info(f"Loaded persistent settings: {settings}")
        except Exception as e:
            logger.error(f"Failed to load settings, using defaults: {e}")
    else:
        logger.info(f"No settings file found, using default (Segment: {default_seg} min).")

    with app_state.runtime_settings_lock:
        app_state.runtime_settings = settings


# ──────────────────────────────────────────────
#  RTSP URL validation
# ──────────────────────────────────────────────
def validate_rtsp_optional(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v2 = str(v).replace("\\", "/").strip()
    return v2 if (v2.startswith("rtsp://") or v2.startswith("rtsps://")) else None
