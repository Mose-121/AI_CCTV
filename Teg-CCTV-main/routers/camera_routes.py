"""
camera_routes.py — Camera CRUD and preview-mode endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from service import app_state
from service.auth import (
    TokenClaims,
    get_claims,
    require_admin,
    require_admin_flexible,
    require_user_flexible,
)
from service.camera_manager import (
    has_access_to_camera,
    infer_sub_url_from_main,
    norm_zone,
    spawn_camera,
    start_sub_preview,
    stop_sub_preview,
    validate_rtsp_optional,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Cameras"])


# ──────────────────────────────────────────────
#  Models
# ──────────────────────────────────────────────
class CameraIn(BaseModel):
    camera_name: str
    url: str
    url2: Optional[str] = None
    zone: str
    comp: Optional[str] = None

    @field_validator("url")
    @classmethod
    def must_be_rtsp(cls, v: str):
        v = (v or "").replace("\\", "/").strip()
        if not (v.startswith("rtsp://") or v.startswith("rtsps://")):
            raise ValueError("url ต้องเป็น RTSP (rtsp:// หรือ rtsps://)")
        return v

    @field_validator("url2")
    @classmethod
    def must_be_rtsp_optional(cls, v: Optional[str]):
        if v is None:
            return v
        v = (v or "").replace("\\", "/").strip()
        if not (v.startswith("rtsp://") or v.startswith("rtsps://")):
            raise ValueError("url2 ต้องเป็น RTSP (rtsp:// หรือ rtsps://)")
        return v


# ──────────────────────────────────────────────
#  GET /cameras
# ──────────────────────────────────────────────
@router.get("/cameras")
def list_cameras(
    dept: Optional[str] = None,
    access: Optional[str] = None,
    claims: Optional[TokenClaims] = Depends(get_claims),
):
    db = app_state.db
    if claims:
        access_list = claims.access
        is_admin = claims.is_admin
    else:
        access_list = [x.strip() for x in (access or "").split(",") if x.strip()] or None
        is_admin = False

    cams = db.get_cameras(allowed_departments=access_list) if not is_admin else db.get_cameras()
    return cams


# ──────────────────────────────────────────────
#  POST /cameras
# ──────────────────────────────────────────────
@router.post("/cameras", status_code=201)
async def add_camera(cam: CameraIn, _: TokenClaims = Depends(require_admin)):
    db = app_state.db
    try:
        new_id = db.add_camera(
            camera_name=cam.camera_name, url=cam.url, url2=cam.url2,
            zone=norm_zone(cam.zone) or "face", comp=cam.comp,
        )
    except Exception as e:
        raise HTTPException(500, f"db error: {e}")

    if new_id is None:
        raise HTTPException(400, "cannot add camera (name duplicate)")

    started = spawn_camera({
        "id": new_id, "camera_name": cam.camera_name,
        "url": cam.url, "url2": cam.url2,
        "zone": norm_zone(cam.zone) or "face", "comp": cam.comp,
    })

    app_state.camera_meta_by_name[cam.camera_name] = {
        "camera_name": cam.camera_name,
        "zone": norm_zone(cam.zone) or "face",
        "url": cam.url, "url2": cam.url2, "comp": cam.comp,
    }

    sub_url = cam.url2 or infer_sub_url_from_main(cam.url)
    if sub_url:
        app_state.preview_mode[cam.camera_name] = "sub"
        start_sub_preview(cam.camera_name, sub_url)
        return {"ok": True, "id": new_id, "started": bool(started), "mode": "sub", "has_sub": True}
    else:
        app_state.preview_mode[cam.camera_name] = "main"
        return {"ok": True, "id": new_id, "started": bool(started), "mode": "main", "has_sub": False}


# ──────────────────────────────────────────────
#  PUT /cameras/{camera_name}
# ──────────────────────────────────────────────
@router.put("/cameras/{camera_name}")
async def update_camera(
    camera_name: str, patch: dict = Body(...), _: TokenClaims = Depends(require_admin)
):
    db = app_state.db
    allowed = {"url", "zone", "comp", "url2", "preview_mode"}
    patch = {k: v for k, v in (patch or {}).items() if k in allowed}

    if "zone" in patch:
        patch["zone"] = norm_zone(patch["zone"]) or "face"
    if "url2" in patch:
        patch["url2"] = validate_rtsp_optional(patch["url2"])
    if not patch:
        return {"ok": True}

    if not db.update_camera(camera_name, patch):
        raise HTTPException(404, "camera not found")

    meta = app_state.camera_meta_by_name.get(camera_name, {})
    meta.update({k: patch[k] for k in patch})
    app_state.camera_meta_by_name[camera_name] = meta

    if "preview_mode" in patch:
        requested_mode = patch["preview_mode"]
        url2 = meta.get("url2")
        stop_sub_preview(camera_name)
        if requested_mode == "sub" and url2:
            start_sub_preview(camera_name, url2)
            app_state.preview_mode[camera_name] = "sub"
        else:
            app_state.preview_mode[camera_name] = "main"
    return {"ok": True}


# ──────────────────────────────────────────────
#  DELETE /cameras/{camera_name}
# ──────────────────────────────────────────────
@router.delete("/cameras/{camera_name}")
def delete_camera(camera_name: str, _: TokenClaims = Depends(require_admin)):
    db = app_state.db
    if not db.delete_camera(camera_name):
        raise HTTPException(status_code=404, detail="camera not found")

    stop_sub_preview(camera_name)

    idx_to_remove = None
    for i, (w, t, _fq, _lq, _sq, rec) in enumerate(app_state.workers):
        if getattr(w, "name", None) == camera_name:
            try:
                w.stop()
                if rec and rec.is_recording():
                    rec.stop_recording()
                t.join(timeout=2.0)
            except Exception:
                pass
            idx_to_remove = i
            break
    if idx_to_remove is not None:
        app_state.workers.pop(idx_to_remove)

    app_state.camera_meta_by_name.pop(camera_name, None)
    app_state.preview_mode.pop(camera_name, None)
    with app_state.latest_lock:
        app_state.latest_frame.pop(camera_name, None)
        app_state.latest_frame_sub.pop(camera_name, None)
        app_state.latest_frame_ts.pop(camera_name, None)
    return {"ok": True}


# ──────────────────────────────────────────────
#  Preview mode
# ──────────────────────────────────────────────
@router.post("/cameras/{camera_name}/preview-mode")
async def set_preview_mode(
    camera_name: str, payload: dict = Body(...),
    claims: TokenClaims = Depends(require_user_flexible),
):
    if not has_access_to_camera(camera_name, claims):
        raise HTTPException(403, f"No access to camera {camera_name}")

    mode = payload.get("mode")
    if mode not in ("main", "sub"):
        raise HTTPException(422, "mode must be 'main' or 'sub'")
    if camera_name not in app_state.camera_meta_by_name:
        raise HTTPException(404, "camera not found")

    meta = app_state.camera_meta_by_name[camera_name]
    url2 = meta.get("url2")
    stop_sub_preview(camera_name)

    if mode == "sub" and url2:
        start_sub_preview(camera_name, url2)
        app_state.preview_mode[camera_name] = "sub"
    else:
        app_state.preview_mode[camera_name] = "main"

    return {"ok": True, "mode": app_state.preview_mode[camera_name]}


@router.get("/cameras/{camera_name}/preview-mode")
async def get_preview_mode(camera_name: str, _: TokenClaims = Depends(require_admin)):
    if camera_name not in app_state.preview_mode:
        return {"mode": "main"}
    return {"mode": app_state.preview_mode[camera_name]}
