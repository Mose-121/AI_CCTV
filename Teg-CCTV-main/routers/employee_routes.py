"""
employee_routes.py — Employee management: enroll, list, update, delete, image slots.
"""

import logging
from typing import List, Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from service import app_state
from service.auth import TokenClaims, require_admin, require_admin_flexible, require_user_flexible
from service.camera_manager import refresh_all_face_workers
from service.face_insight import get_enroll_face_app, infer_hint

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Employees"])


# ──────────────────────────────────────────────
#  POST /employees/enroll
# ──────────────────────────────────────────────
@router.post("/employees/enroll")
async def enroll_employee(
    emp_id: str = Form(...),
    name: str = Form(...),
    department: str = Form(...),
    files: List[UploadFile] = File(...),
    _: TokenClaims = Depends(require_admin),
):
    db = app_state.db
    if db is None:
        raise HTTPException(500, "database not ready")
    if not files:
        raise HTTPException(400, "no files uploaded")

    enroll_app = get_enroll_face_app()

    saved_any = False
    errors = []
    for uf in files:
        try:
            content = await uf.read()
            nparr = np.frombuffer(content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                errors.append(f"{uf.filename}: Cannot decode image")
                continue

            faces = enroll_app.get(img)
            if not faces or getattr(faces[0], "embedding", None) is None:
                errors.append(f"{uf.filename}: No face detected")
                continue

            emb = faces[0].embedding.astype(np.float32)
            view_hint = infer_hint(uf.filename)
            ok = db.add_employee(
                emp_id=emp_id, name=name, department=department,
                image_data=content, embedding=emb.tobytes(), view_hint=view_hint,
            )
            if ok:
                saved_any = True
        except Exception as e:
            logger.error(f"[ENROLL] Error processing {uf.filename}: {e}", exc_info=True)
            errors.append(f"{uf.filename}: Server error - {str(e)}")

    if not saved_any:
        raise HTTPException(422, detail={"message": "No valid new faces could be processed.", "errors": errors})

    refresh_all_face_workers()
    return {"ok": True, "emp_id": emp_id, "name": name, "department": department, "errors": errors}


# ──────────────────────────────────────────────
#  GET /employees
# ──────────────────────────────────────────────
@router.get("/employees")
def list_employees(claims: TokenClaims = Depends(require_user_flexible)):
    db = app_state.db
    if not db:
        raise HTTPException(500, "Database not connected")
    try:
        return db.list_employees()
    except AttributeError:
        raise HTTPException(500, "Server is missing 'db.list_employees()' method.")
    except Exception as e:
        raise HTTPException(500, f"Error listing employees: {e}")


# ──────────────────────────────────────────────
#  GET /employees/{emp_id}
# ──────────────────────────────────────────────
@router.get("/employees/{emp_id}")
def get_employee_details(emp_id: str, _: TokenClaims = Depends(require_admin)):
    db = app_state.db
    if db is None:
        raise HTTPException(500, "database not ready")
    details = db.get_employee_details(emp_id)
    if not details:
        raise HTTPException(404, "Employee not found")
    return details


# ──────────────────────────────────────────────
#  PUT /employees/{emp_id}/info
# ──────────────────────────────────────────────
class EmployeeInfoUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None


@router.put("/employees/{emp_id}/info")
def update_employee_info(
    emp_id: str, payload: EmployeeInfoUpdate, _: TokenClaims = Depends(require_admin)
):
    db = app_state.db
    if db is None:
        raise HTTPException(500, "database not ready")
    ok = db.update_employee_info(emp_id, name=payload.name, department=payload.department)
    if not ok:
        raise HTTPException(404, "Employee not found or update failed")
    refresh_all_face_workers()
    return {"ok": True, "emp_id": emp_id}


# ──────────────────────────────────────────────
#  POST /employees/{emp_id}/update  — add image to existing employee
# ──────────────────────────────────────────────
@router.post("/employees/{emp_id}/update")
async def update_employee_add_image(
    emp_id: str,
    name: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    _: TokenClaims = Depends(require_admin),
):
    db = app_state.db
    if db is None:
        raise HTTPException(500, "database not ready")
    if not files:
        raise HTTPException(400, "no new files uploaded")
    if not db.employee_exists(emp_id):
        raise HTTPException(404, f"Employee with emp_id {emp_id} not found.")

    uf = files[0]
    enroll_app = get_enroll_face_app()

    try:
        content = await uf.read()
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(422, f"{uf.filename}: Cannot decode image")
        faces = enroll_app.get(img)
        if not faces or getattr(faces[0], "embedding", None) is None:
            raise HTTPException(422, f"{uf.filename}: No face detected")

        emb = faces[0].embedding.astype(np.float32)
        view_hint = infer_hint(uf.filename)
        ok = db.add_employee(
            emp_id=emp_id, name=name, department=department,
            image_data=content, embedding=emb.tobytes(),
            view_hint=view_hint, aligned_image_data=None,
        )
        if not ok:
            raise HTTPException(409, "All 5 image slots are full. Please delete an old image first.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Server error: {str(e)}")

    refresh_all_face_workers()
    return {"ok": True, "emp_id": emp_id, "new_image_added": True}


# ──────────────────────────────────────────────
#  DELETE /employees/{emp_id}/slot/{slot_num}
# ──────────────────────────────────────────────
@router.delete("/employees/{emp_id}/slot/{slot_num}")
def delete_employee_slot(
    emp_id: str, slot_num: int, _: TokenClaims = Depends(require_admin)
):
    db = app_state.db
    if db is None:
        raise HTTPException(500, "database not ready")
    if slot_num not in (1, 2, 3, 4, 5):
        raise HTTPException(422, "Slot number must be 1, 2, 3, 4, or 5")
    try:
        ok = db.clear_employee_slot(emp_id, slot_num)
        if not ok:
            raise HTTPException(404, "Employee not found or slot already empty")
        refresh_all_face_workers()
        return {"ok": True, "emp_id": emp_id, "slot_cleared": slot_num}
    except Exception as e:
        raise HTTPException(500, str(e))


# ──────────────────────────────────────────────
#  DELETE /employees/{emp_id}
# ──────────────────────────────────────────────
@router.delete("/employees/{emp_id}")
def delete_employee(emp_id: str, _: TokenClaims = Depends(require_admin)):
    db = app_state.db
    if not db.delete_employee(emp_id):
        raise HTTPException(status_code=404, detail="employee not found")
    return {"ok": True}
