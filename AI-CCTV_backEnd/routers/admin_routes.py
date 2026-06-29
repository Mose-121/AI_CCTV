"""
admin_routes.py — Admin endpoints: shutdown, segment settings, health status.
"""

import asyncio
import logging
import os

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from service import app_state
from service.auth import TokenClaims, require_admin
from service.camera_manager import (
    generate_health_status,
    save_persistent_settings,
    stop_sub_preview,
)
from service.config import ADMIN_TOKEN

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin"])


# ──────────────────────────────────────────────
#  POST /admin/shutdown
# ──────────────────────────────────────────────
@router.post("/admin/shutdown")
async def admin_shutdown(payload: dict = Body(...)):
    if payload.get("token") != ADMIN_TOKEN:
        raise HTTPException(403, "forbidden")
    for item in app_state.workers:
        worker, t, _fq, _lq, _sq, rec = item
        try:
            worker.stop()
            if rec and rec.is_recording():
                rec.stop_recording()
            t.join(timeout=2.0)
        except Exception:
            pass
    try:
        for name in list(app_state.sub_preview_threads.keys()):
            stop_sub_preview(name)
    except Exception:
        pass
    await asyncio.sleep(0.2)
    os._exit(0)


# ──────────────────────────────────────────────
#  POST /admin/settings/segment
# ──────────────────────────────────────────────
class SegmentUpdate(BaseModel):
    minutes: int


@router.post("/admin/settings/segment")
def admin_set_segment_minutes(
    payload: SegmentUpdate, _: TokenClaims = Depends(require_admin)
):
    new_minutes = max(1, min(payload.minutes, 120))

    with app_state.runtime_settings_lock:
        app_state.runtime_settings["SEGMENT_MINUTES"] = new_minutes

    save_persistent_settings()

    updated_count = 0
    for item in app_state.workers:
        recorder = item[5] if len(item) > 5 else None
        if recorder and hasattr(recorder, "update_segment_minutes"):
            try:
                recorder.update_segment_minutes(new_minutes)
                updated_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to update segment for {getattr(recorder, '_camera_id', '?')}: {e}"
                )

    logger.info(f"Admin set segment to {new_minutes} mins. {updated_count} recorders updated.")
    return {
        "ok": True,
        "new_segment_minutes": new_minutes,
        "workers_updated": updated_count,
    }


# ──────────────────────────────────────────────
#  GET /health
# ──────────────────────────────────────────────
@router.get("/health")
def health_check():
    return generate_health_status()


# ──────────────────────────────────────────────
#  GET / (root)
# ──────────────────────────────────────────────
@router.get("/")
def root():
    return {"status": "ok", "service": "Teg-CCTV", "version": "2.0"}
