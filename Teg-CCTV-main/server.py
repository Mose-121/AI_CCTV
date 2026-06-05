"""
server.py — Slim entry point for the Teg-CCTV backend.

All business logic has been moved to:
  - service/   : config, auth, database, camera_manager, face_insight, workers, utils
  - routers/   : auth, cameras, employees, users, recordings, reports, streaming, admin
"""

import asyncio
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Service layer ────────────────────────────
from service import app_state
from service.camera_manager import (
    camera_health_monitor_thread,
    load_persistent_settings,
    spawn_camera,
)
from service.config import TZ
from service.database import Database

# ── Routers ──────────────────────────────────
from routers.admin_routes import router as admin_router
from routers.auth_routes import router as auth_router
from routers.camera_routes import router as camera_router
from routers.employee_routes import router as employee_router
from routers.recording_routes import router as recording_router
from routers.report_routes import router as report_router
from routers.streaming_routes import router as streaming_router
from routers.user_routes import router as user_router

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Application Lifespan (startup / shutdown)
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("=" * 60)
    logger.info("  Teg-CCTV Server v2.0 — Starting...")
    logger.info("=" * 60)

    # 1. Database
    try:
        app_state.db = Database()
        logger.info("✅ Database connected")
    except Exception as e:
        logger.critical(f"❌ Database connection failed: {e}")

    # 2. Load persistent settings (segment minutes, etc.)
    load_persistent_settings()

    # 3. Spawn cameras from DB
    if app_state.db:
        cameras = app_state.db.get_cameras() or []
        logger.info(f"📷 Found {len(cameras)} cameras in DB")
        for cam in cameras:
            try:
                spawn_camera(cam)
            except Exception as e:
                logger.error(f"❌ Failed to spawn camera {cam.get('camera_name')}: {e}")

    # 4. Health monitor
    loop = asyncio.get_running_loop()
    threading.Thread(
        target=camera_health_monitor_thread, args=(loop,), daemon=True
    ).start()

    logger.info("✅ Startup complete")
    yield

    # ── Shutdown ──
    logger.info("🔻 Shutting down...")
    for w, t, _fq, _lq, _sq, rec in app_state.workers:
        try:
            w.stop()
            if rec and rec.is_recording():
                rec.stop_recording()
            t.join(timeout=2.0)
        except Exception:
            pass
    logger.info("✅ Shutdown complete")


# ──────────────────────────────────────────────
#  FastAPI Application
# ──────────────────────────────────────────────
app = FastAPI(
    title="Teg-CCTV API",
    version="2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(camera_router)
app.include_router(employee_router)
app.include_router(recording_router)
app.include_router(report_router)
app.include_router(streaming_router)
app.include_router(user_router)


# ──────────────────────────────────────────────
#  Run
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    KEEP_ALIVE_SEC = 24 * 60 * 60 * 365
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        lifespan="on",
        timeout_keep_alive=KEEP_ALIVE_SEC,
    )
