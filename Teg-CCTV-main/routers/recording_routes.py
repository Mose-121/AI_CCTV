"""
recording_routes.py — Recording list and file-serving endpoints.
"""

import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from service import app_state
from service.auth import TokenClaims, require_user, require_user_flexible
from service.config import RECORD_ROOT, TZ

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Recordings"])


# ──────────────────────────────────────────────
#  GET /recordings
# ──────────────────────────────────────────────
@router.get("/recordings")
async def list_recordings(
    claims: TokenClaims = Depends(require_user),
    camera: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    person_name: Optional[str] = Query(None),
):
    import datetime as dt
    import re

    files = []
    try:
        for dept in os.listdir(RECORD_ROOT):
            dept_path = os.path.join(RECORD_ROOT, dept)
            if not os.path.isdir(dept_path):
                continue
            for zone_dir in os.listdir(dept_path):
                zone_path = os.path.join(dept_path, zone_dir)
                if not os.path.isdir(zone_path):
                    continue
                for cam_dir in os.listdir(zone_path):
                    cam_path = os.path.join(zone_path, cam_dir)
                    if not os.path.isdir(cam_path):
                        continue

                    cam_meta = app_state.camera_meta_by_name.get(cam_dir)
                    cam_comp = cam_meta.get("comp") if cam_meta else dept
                    if not claims.is_admin and cam_comp and cam_comp not in claims.access:
                        continue

                    for date_dir in os.listdir(cam_path):
                        date_path = os.path.join(cam_path, date_dir)
                        if not os.path.isdir(date_path):
                            continue
                        for fn in os.listdir(date_path):
                            if fn.lower().endswith(".mp4"):
                                full = os.path.join(date_path, fn)
                                try:
                                    stat = os.stat(full)
                                    files.append({
                                        "file": fn,
                                        "size_bytes": stat.st_size,
                                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                        "department": dept,
                                        "zone": zone_dir,
                                        "camera": cam_dir,
                                        "date": date_dir,
                                    })
                                except FileNotFoundError:
                                    continue
    except Exception as e:
        logger.error(f"[ERROR] list recordings error: {e}")
        raise HTTPException(500, f"list recordings error: {e}")

    files.sort(key=lambda x: x["modified"], reverse=True)

    filtered = files
    if camera:
        filtered = [f for f in filtered if f.get("camera") == camera]
    if zone:
        filtered = [f for f in filtered if f.get("zone") == zone]
    if date:
        filtered = [f for f in filtered if f.get("date") == date]

    if person_name and person_name.strip() and app_state.db:
        import pytz

        bangkok_tz = pytz.timezone("Asia/Bangkok")
        FILENAME_TIME_RE = re.compile(r"_(\d{2})(\d{2})(\d{2})\.mp4$", re.IGNORECASE)

        try:
            start_dt = bangkok_tz.localize(
                dt.datetime.strptime(f"{date} 00:00:00", "%Y-%m-%d %H:%M:%S")
            )
            end_dt = bangkok_tz.localize(
                dt.datetime.strptime(f"{date} 23:59:59", "%Y-%m-%d %H:%M:%S")
            )
            person_timestamps = app_state.db.get_timestamps_for_person(
                start_dt, end_dt, camera, person_name
            )
        except Exception as e:
            logger.error(f"Failed to get person timestamps: {e}")
            person_timestamps = []

        if not person_timestamps:
            return []

        files_with_person = []
        for file_item in filtered:
            try:
                with app_state.runtime_settings_lock:
                    seg_min = app_state.runtime_settings.get("SEGMENT_MINUTES", 15)
                f_start, f_end = _get_time_range_from_filename(
                    file_item["date"], file_item["file"], seg_min
                )
                if any(f_start <= ts <= f_end for ts in person_timestamps):
                    files_with_person.append(file_item)
            except Exception as e:
                logger.warning(f"Could not parse time range for {file_item['file']}: {e}")
        return files_with_person

    return filtered


# ──────────────────────────────────────────────
#  GET /recordings/{department}/{zone}/{camera}/{date}/{filename}
# ──────────────────────────────────────────────
@router.get("/recordings/{department}/{zone}/{camera}/{date}/{filename}")
async def fetch_recording(
    department: str, zone: str, camera: str, date: str, filename: str,
    claims: TokenClaims = Depends(require_user_flexible),
):
    cam_meta = app_state.camera_meta_by_name.get(camera)
    cam_comp = cam_meta.get("comp") if cam_meta else department

    user_access = claims.access or []
    if not claims.is_admin and cam_comp and cam_comp not in user_access:
        logger.warning(f"Access Denied: User '{claims.sub}' -> camera '{camera}' (Comp: {cam_comp})")
        raise HTTPException(403, f"No access to recordings for camera {camera}")

    safe_base = os.path.normpath(RECORD_ROOT)

    def sanitize_part(part: str) -> str:
        return part.replace("..", "").replace("/", "").replace("\\", "")

    path = os.path.join(
        safe_base,
        sanitize_part(department), sanitize_part(zone),
        sanitize_part(camera), sanitize_part(date), sanitize_part(filename),
    )
    abs_path = os.path.abspath(path)
    abs_base = os.path.abspath(safe_base)
    if not abs_path.startswith(abs_base):
        raise HTTPException(403, "Forbidden path")
    if not os.path.isfile(abs_path):
        raise HTTPException(404, "File not found")

    return FileResponse(abs_path, media_type="video/mp4", filename=sanitize_part(filename))


# ──────────────────────────────────────────────
#  Time range helper
# ──────────────────────────────────────────────
def _get_time_range_from_filename(date_str: str, filename: str, segment_minutes: int):
    import datetime as dt
    import re

    import pytz

    bangkok_tz = pytz.timezone("Asia/Bangkok")
    FILENAME_TIME_RE = re.compile(r"_(\d{2})(\d{2})(\d{2})\.mp4$", re.IGNORECASE)

    match = FILENAME_TIME_RE.search(filename)
    start_dt_obj = None
    if match:
        try:
            hh, mm, ss = match.groups()
            start_str = f"{date_str} {hh}:{mm}:{ss}"
            start_dt_obj = dt.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            start_dt_obj = None

    if start_dt_obj is None:
        start_dt_obj = dt.datetime.strptime(f"{date_str} 00:00:00", "%Y-%m-%d %H:%M:%S")

    start_dt = bangkok_tz.localize(start_dt_obj)
    if not match:
        end_dt = start_dt + dt.timedelta(days=1, seconds=-1)
    else:
        end_dt = start_dt + dt.timedelta(minutes=segment_minutes)
    return start_dt, end_dt
