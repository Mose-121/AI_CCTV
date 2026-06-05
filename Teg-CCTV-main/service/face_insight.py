"""
face_insight.py — InsightFace model setup (runtime + enrollment) and face utility helpers.
"""

import logging
import os
from typing import List, Optional

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from insightface.utils.face_align import norm_crop as _norm_crop_112

from service.config import ENR_MIN_BLUR_VAR, ENR_MIN_DET_SCORE, ENR_MIN_FACE_PX

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  ORT Provider selection
# ──────────────────────────────────────────────
def _get_ort_providers() -> list:
    req = [
        p.strip()
        for p in os.getenv(
            "INSIGHTFACE_PROVIDERS", "CUDAExecutionProvider,CPUExecutionProvider"
        ).split(",")
        if p.strip()
    ]
    try:
        import onnxruntime as ort

        avail = set(ort.get_available_providers())
        logger.info(f"[INSIGHT] Available providers: {list(avail)}")
        use = (
            ["CUDAExecutionProvider"]
            if "CUDAExecutionProvider" in avail
            else [p for p in req if p in avail] or ["CPUExecutionProvider"]
        )
        logger.info(f"[INSIGHT] Requested={req} -> Using={use}")
        return use
    except Exception as e:
        logger.warning(f"[INSIGHT] onnxruntime not available: {e}, fallback to CPU.")
        return ["CPUExecutionProvider"]


# ──────────────────────────────────────────────
#  Dual face app (runtime + enroll)
# ──────────────────────────────────────────────
_runtime_face_app = None
_enroll_face_app = None


def _build_face_app(det_size, det_thresh):
    providers = _get_ort_providers()
    app = FaceAnalysis(
        name=os.getenv("FACE_MODEL_NAME", "buffalo_l"), providers=providers
    )
    ctx_id = 0 if "CUDAExecutionProvider" in providers else -1
    app.prepare(ctx_id=ctx_id, det_size=det_size, det_thresh=det_thresh)
    return app


def get_runtime_face_app():
    global _runtime_face_app
    if _runtime_face_app is None:
        w, h = os.getenv("RUNTIME_DET_SIZE", "1280,1280").split(",")
        thr = float(os.getenv("RUNTIME_DET_THRESH", "0.5"))
        _runtime_face_app = _build_face_app((int(w), int(h)), thr)
        logger.info(f"[Face] Runtime FaceAnalysis ready ({w}x{h}, thr={thr})")
    return _runtime_face_app


def get_enroll_face_app():
    global _enroll_face_app
    if _enroll_face_app is None:
        w, h = os.getenv("ENROLL_DET_SIZE", "512,512").split(",")
        thr = float(os.getenv("ENROLL_DET_THRESH", "0.3"))
        _enroll_face_app = _build_face_app((int(w), int(h)), thr)
        logger.info(f"[Face] Enroll FaceAnalysis ready ({w}x{h}, thr={thr})")
    return _enroll_face_app


# ──────────────────────────────────────────────
#  Compute embedding from image
# ──────────────────────────────────────────────
def compute_embedding(image: np.ndarray) -> Optional[np.ndarray]:
    app = get_runtime_face_app()
    try:
        faces = app.get(image)
        if not faces:
            logger.warning("[compute_embedding] No faces detected in image")
            return None
        return faces[0].embedding
    except Exception as e:
        logger.error(f"[compute_embedding] Error: {e}")
        return None


# ──────────────────────────────────────────────
#  L2 normalization
# ──────────────────────────────────────────────
def l2norm_np(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=-1, keepdims=True) + 1e-9
    return (x / n).astype(np.float32)


# ──────────────────────────────────────────────
#  Enrollment helpers
# ──────────────────────────────────────────────
def resize_if_too_big(img: np.ndarray, max_side: int) -> np.ndarray:
    h, w = img.shape[:2]
    side = max(h, w)
    if side <= max_side:
        return img
    scale = max_side / float(side)
    return cv2.resize(
        img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
    )


def lap_var(img_bgr: np.ndarray) -> float:
    g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def best_face(enroll_app, img: np.ndarray):
    faces = enroll_app.get(img) or []
    if not faces:
        return None
    good = []
    for f in faces:
        x1, y1, x2, y2 = f.bbox.astype(int).tolist()
        w, h = max(0, x2 - x1), max(0, y2 - y1)
        if min(w, h) < ENR_MIN_FACE_PX:
            continue
        det_score = float(getattr(f, "det_score", 0.0) or 0.0)
        if det_score < ENR_MIN_DET_SCORE:
            continue
        crop = img[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
        if crop.size == 0:
            continue
        if lap_var(crop) < ENR_MIN_BLUR_VAR:
            continue
        good.append(f)
    if not good:
        return None
    good.sort(
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True
    )
    return good[0]


def aligned_112(img, face):
    try:
        al = _norm_crop_112(img, landmark=getattr(face, "kps", None), image_size=112)
        return al if al is not None and al.shape[:2] == (112, 112) else None
    except Exception:
        return None


def embedding_from(face_app, face, aligned: Optional[np.ndarray]) -> Optional[np.ndarray]:
    emb = getattr(face, "embedding", None)
    if emb is not None and emb.size == 512:
        return l2norm_np(emb.astype(np.float32).reshape(-1))
    if aligned is None:
        return None
    rec_model = (
        face_app.models.get("recognition") if hasattr(face_app, "models") else None
    )
    if rec_model is None:
        return None
    try:
        feat = rec_model.get_feat(aligned).reshape(-1).astype(np.float32)
        return l2norm_np(feat)
    except Exception:
        return None


def load_emp_existing_embeddings(db, emp_id: str) -> List[np.ndarray]:
    try:
        if hasattr(db, "load_employee_embeddings"):
            rows = db.load_employee_embeddings(emp_id)
        elif hasattr(db, "get_employee_embeddings"):
            rows = db.get_employee_embeddings(emp_id)
        else:
            rows = []
        out = []
        for r in rows:
            e = (
                np.frombuffer(r, dtype=np.float32)
                if isinstance(r, (bytes, bytearray))
                else np.array(r, dtype=np.float32)
            )
            if e.size == 512:
                out.append(l2norm_np(e))
        return out
    except Exception:
        return []


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b)


def jpeg_bytes(img_bgr: np.ndarray, q: int = 95) -> bytes:
    ok, buf = cv2.imencode(".jpg", img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), q])
    return buf.tobytes() if ok else b""


# ──────────────────────────────────────────────
#  View hint inference
# ──────────────────────────────────────────────
_HINT_KEYWORDS = {
    "center": ("center", "front", "straight", "middle", "mid"),
    "left": ("left", "l_", "_l", "-l", "(l)", "yawleft"),
    "right": ("right", "r_", "_r", "-r", "(r)", "yawright"),
}


def guess_view_hint(filename: str) -> str:
    if not filename:
        return "center"
    fn = filename.lower()
    for hint, keys in _HINT_KEYWORDS.items():
        if any(k in fn for k in keys):
            return hint
    return "center"


def infer_hint(filename: str) -> Optional[str]:
    fn = (filename or "").lower()
    if "left" in fn:
        return "left"
    if "right" in fn:
        return "right"
    if any(k in fn for k in ("center", "front", "straight", "mid", "middle")):
        return "center"
    return None
