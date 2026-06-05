"""
report_routes.py — Reporting endpoints: all reports, by-video-file, camera-events.
"""

import datetime as dt
import logging
from typing import Optional

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query

from service import app_state
from service.auth import TokenClaims, require_admin, require_user, require_user_flexible
from service.camera_manager import norm_zone

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Reports"])

bangkok_tz = pytz.timezone("Asia/Bangkok")


def _thai_to_arabic(s: str) -> str:
    return s.translate(str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789"))


def _normalize_dt(s: str, is_end: bool) -> str:
    from datetime import datetime as _dt

    if len(s) == 10:
        return f"{s} {'23:59:59' if is_end else '00:00:00'}"
    try:
        _dt.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(400, f"Invalid datetime format: {s}")
    return s


# ──────────────────────────────────────────────
#  GET /reports
# ──────────────────────────────────────────────
@router.get("/reports")
async def report_all(
    start: str = Query(..., description="YYYY-MM-DD[ HH:MM:SS]"),
    end: str = Query(..., description="YYYY-MM-DD[ HH:MM:SS]"),
    department: Optional[str] = Query(None, description="filter by camera's comp"),
    type: Optional[str] = Query(None, description="face | car"),
    q: Optional[str] = Query(None, description="search: plate/name/department/province/camera"),
    limit: int = Query(500, ge=1, le=5000),
    claims: TokenClaims = Depends(require_user),
):
    try:
        start = _thai_to_arabic(start.strip())
        end = _thai_to_arabic(end.strip())

        start_str = _normalize_dt(start, False)
        end_str = _normalize_dt(end, True)

        start_dt = bangkok_tz.localize(dt.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S"))
        end_dt = bangkok_tz.localize(dt.datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S"))

        type_ = norm_zone(type) if type else None
        if type_ and type_ not in ("face", "car"):
            raise HTTPException(422, "type must be 'face' or 'car'")

        dep_value = (department or "").strip() if department is not None else None

        db = app_state.db
        cur = db.cursor
        access_list = list(claims.access or [])
        allowed_cams = [
            a.split("cam:", 1)[1] if a.lower().startswith("cam:") else a
            for a in access_list
        ]
        allowed_depts = [a for a in access_list if a and a not in app_state.camera_meta_by_name]
        if claims.department and claims.department not in allowed_depts:
            allowed_depts.append(claims.department)

        sql = """
        WITH face AS (
            SELECT f.timestamp AS ts, f.camera_name, 'face' AS kind,
                   f.full_name AS subject, f.department AS meta1, f.emp_id AS meta2,
                   f.confidence, f.similarity
            FROM face_detection_details f
            WHERE f.timestamp BETWEEN %s AND %s
        ),
        car AS (
            SELECT cl.timestamp AT TIME ZONE 'Asia/Bangkok' AS ts, cl.camera_name, 'car' AS kind,
                   cl.plate_number AS subject, cl.province AS meta1, cl.status AS meta2,
                   NULL::double precision AS confidence, NULL::double precision AS similarity
            FROM car_log cl
            WHERE cl.timestamp AT TIME ZONE 'Asia/Bangkok' BETWEEN %s AND %s
        ),
        raw AS (SELECT * FROM face UNION ALL SELECT * FROM car)
        SELECT r.ts, r.camera_name, c.zone, r.kind, r.subject, r.meta1, r.meta2, r.confidence, r.similarity
        FROM raw r JOIN cameras c ON c.camera_name = r.camera_name
        WHERE 1=1
        """
        params = [start_dt, end_dt, start_dt, end_dt]

        if not claims.is_admin:
            conds = []
            if allowed_depts:
                conds.append("c.comp = ANY(%s)")
                params.append(allowed_depts)
            if allowed_cams:
                conds.append("r.camera_name = ANY(%s)")
                params.append(allowed_cams)
            if conds:
                sql += " AND (" + " OR ".join(conds) + ")"
            else:
                sql += " AND 1=0"

        if dep_value is not None:
            if dep_value in ("", "ไม่มีแผนก", "None"):
                sql += " AND c.comp IS NULL"
            else:
                sql += " AND c.comp = %s"
                params.append(dep_value)

        if type_ in ("face", "car"):
            sql += " AND r.kind = %s"
            params.append(type_)

        if q:
            tokens = [t for t in q.strip().split() if t]
            for t in tokens:
                like = f"%{t}%"
                sql += """
                AND (r.subject ILIKE %s OR r.meta1 ILIKE %s OR r.meta2 ILIKE %s OR r.camera_name ILIKE %s)
                """
                params.extend([like, like, like, like])

        sql += " ORDER BY r.ts DESC LIMIT %s"
        params.append(limit)

        cur.execute(sql, params)
        rows = cur.fetchall()

        items = []
        for ts, cam_name, z, kind, subject, meta1, meta2, confidence, similarity in rows:
            base = {"type": kind, "timestamp": ts.isoformat(), "camera_name": cam_name, "zone": z}
            if kind == "face":
                base.update({
                    "full_name": subject, "department": meta1, "emp_id": meta2,
                    "confidence": confidence, "similarity": similarity,
                })
            else:
                base.update({"plate": subject, "province": meta1, "status": meta2})
            items.append(base)

        return {"count": len(items), "items": items}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] /reports - {e}")
        try:
            app_state.db.log_error("report_all", str(e), None)
        except Exception:
            pass
        raise HTTPException(500, f"report error: {e}")


# ──────────────────────────────────────────────
#  GET /reports/by-video-file
# ──────────────────────────────────────────────
@router.get("/reports/by-video-file")
async def report_by_video_file(
    filename: str = Query(...),
    camera: str = Query(...),
    zone: str = Query(...),
    date: str = Query(..., description="YYYY-MM-DD"),
    claims: TokenClaims = Depends(require_user_flexible),
):
    cam_meta = app_state.camera_meta_by_name.get(camera)
    cam_comp = cam_meta.get("comp") if cam_meta else None
    user_access = claims.access or []
    if not claims.is_admin and cam_comp and cam_comp not in user_access:
        raise HTTPException(403, f"No access to reports for camera {camera}")

    try:
        import re

        FILENAME_TIME_RE = re.compile(r"_(\d{2})(\d{2})(\d{2})\.mp4$", re.IGNORECASE)

        with app_state.runtime_settings_lock:
            current_segment = app_state.runtime_settings.get("SEGMENT_MINUTES", 15)

        match = FILENAME_TIME_RE.search(filename)
        start_dt_obj = None
        if match:
            try:
                hh, mm, ss = match.groups()
                start_dt_obj = dt.datetime.strptime(f"{date} {hh}:{mm}:{ss}", "%Y-%m-%d %H:%M:%S")
            except ValueError:
                start_dt_obj = None
        if start_dt_obj is None:
            start_dt_obj = dt.datetime.strptime(f"{date} 00:00:00", "%Y-%m-%d %H:%M:%S")

        start_dt = bangkok_tz.localize(start_dt_obj)
        end_dt = (
            start_dt + dt.timedelta(days=1, seconds=-1)
            if not match
            else start_dt + dt.timedelta(minutes=current_segment)
        )

        db = app_state.db
        cur = db.cursor
        sql = """
        WITH face AS (
            SELECT f.timestamp AS ts, f.camera_name, 'face' AS kind,
                   f.full_name AS subject, f.department AS meta1, f.emp_id AS meta2
            FROM face_detection_details f
            WHERE f.timestamp BETWEEN %s AND %s AND f.camera_name = %s
        ),
        car AS (
            SELECT cl.timestamp AT TIME ZONE 'Asia/Bangkok' AS ts, cl.camera_name, 'car' AS kind,
                   cl.plate_number AS subject, cl.province AS meta1, cl.status AS meta2
            FROM car_log cl
            WHERE cl.timestamp AT TIME ZONE 'Asia/Bangkok' BETWEEN %s AND %s AND cl.camera_name = %s
        ),
        raw AS (SELECT * FROM face UNION ALL SELECT * FROM car)
        SELECT r.ts, r.camera_name, r.kind, r.subject, r.meta1, r.meta2
        FROM raw r ORDER BY r.ts ASC
        """
        params = [start_dt, end_dt, camera, start_dt, end_dt, camera]
        cur.execute(sql, params)
        rows = cur.fetchall()

        items = []
        for ts, cam_name, kind, subject, meta1, meta2 in rows:
            base = {"type": kind, "timestamp": ts.isoformat(), "camera_name": cam_name}
            if kind == "face":
                base.update({"full_name": subject, "department": meta1, "emp_id": meta2})
            else:
                base.update({"plate": subject, "province": meta1, "status": meta2})
            items.append(base)
        return {"count": len(items), "items": items}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] /reports/by-video-file - {e}", exc_info=True)
        raise HTTPException(500, f"Report by file error: {e}")


# ──────────────────────────────────────────────
#  GET /reports/camera-events
# ──────────────────────────────────────────────
@router.get("/reports/camera-events")
def get_camera_events_report(
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    _: TokenClaims = Depends(require_admin),
):
    db = app_state.db
    if not db:
        raise HTTPException(500, "Database not connected")
    try:
        items = db.get_camera_events(start, end)
        return {"items": items}
    except Exception as e:
        logger.error(f"[API /reports/camera-events] Error: {e}", exc_info=True)
        raise HTTPException(500, str(e))
