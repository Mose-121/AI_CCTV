"""
config.py — Single source of truth for all environment variables, constants, and paths.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pytz
from pydantic import BaseModel

# ──────────────────────────────────────────────
#  dotenv (optional)
# ──────────────────────────────────────────────
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception as e:
    print(f"[WARN] dotenv import failed: {e}")

# ──────────────────────────────────────────────
#  Timezone & Logging
# ──────────────────────────────────────────────
TZ = pytz.timezone("Asia/Bangkok")


class _ThaiFormatter(logging.Formatter):
    """Formatter that shows Asia/Bangkok local time."""

    def converter(self, timestamp):
        dt_ = datetime.fromtimestamp(timestamp)
        return TZ.localize(dt_)

    def formatTime(self, record, datefmt=None):
        dt_ = self.converter(record.created)
        return dt_.strftime(datefmt) if datefmt else dt_.isoformat(timespec="milliseconds")


_handler = logging.StreamHandler()
_handler.setFormatter(_ThaiFormatter("[%(asctime)s] [%(levelname)s] %(message)s"))
logging.root.addHandler(_handler)
logging.root.setLevel(logging.INFO)
logging.getLogger("asyncio").setLevel(logging.ERROR)

logger = logging.getLogger("config")
logger.info(f"Current real time: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}")

# ──────────────────────────────────────────────
#  Paths
# ──────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = APP_DIR / "server_settings.json"
BIN_DIR = APP_DIR / "bin"

# Add bundled ffmpeg to PATH if present
if "FFMPEG_BIN" not in os.environ:
    ff = BIN_DIR / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if ff.exists():
        os.environ["FFMPEG_BIN"] = str(ff)
os.environ["PATH"] = str(BIN_DIR) + os.pathsep + os.environ.get("PATH", "")

RECORD_ROOT = os.getenv(
    "RECORD_ROOT", os.path.abspath(os.path.join(os.getcwd(), "recordings"))
)
os.makedirs(RECORD_ROOT, exist_ok=True)

# ──────────────────────────────────────────────
#  Auth / JWT
# ──────────────────────────────────────────────
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

# ──────────────────────────────────────────────
#  RTSP / OpenCV / FFmpeg
# ──────────────────────────────────────────────
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "rtsp_transport;tcp|max_delay;500000|stimeout;5000000|buffer_size;2097152",
)

# ──────────────────────────────────────────────
#  InsightFace (face detection / recognition)
# ──────────────────────────────────────────────
os.environ.setdefault("ENROLL_DET_SIZE", "512,512")
os.environ.setdefault("ENROLL_DET_THRESH", "0.30")
os.environ.setdefault("RUNTIME_DET_SIZE", "1280,1280")
os.environ.setdefault("RUNTIME_DET_THRESH", "0.50")
os.environ.setdefault("FACE_MODEL_NAME", "buffalo_l")

# ──────────────────────────────────────────────
#  Preview / MJPG
# ──────────────────────────────────────────────
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "80"))
JPEG_OPTIMIZE = int(os.getenv("JPEG_OPTIMIZE", "1"))
MAX_JPEG_SIDE = int(os.getenv("MAX_JPEG_SIDE", "1280"))
STALE_SEC = float(os.getenv("STALE_SEC", "2.5"))
BLACK_H = int(os.getenv("BLACK_H", "480"))
BLACK_W = int(os.getenv("BLACK_W", "854"))
BLACK_480P = np.zeros((BLACK_H, BLACK_W, 3), dtype=np.uint8)

RECORD_FPS_HINT = int(os.getenv("RECORD_FPS_HINT", "25"))

# ──────────────────────────────────────────────
#  Enrollment quality thresholds
# ──────────────────────────────────────────────
ENR_MAX_IMG_SIDE = int(os.getenv("ENR_MAX_IMG_SIDE", "3000"))
ENR_MIN_FACE_PX = int(os.getenv("ENR_MIN_FACE_PX", "140"))
ENR_MIN_BLUR_VAR = float(os.getenv("ENR_MIN_BLUR_VAR", "120"))
ENR_MIN_DET_SCORE = float(os.getenv("ENR_MIN_DET_SCORE", "0.60"))
ENR_DUPE_SIM_THRESH = float(os.getenv("ENR_DUPE_SIM_THRESH", "0.88"))
ENR_STORE_ALIGNED = os.getenv("ENR_STORE_ALIGNED", "true").lower() in ("1", "true", "yes")

# ──────────────────────────────────────────────
#  Health monitoring
# ──────────────────────────────────────────────
HEALTH_CHECK_INTERVAL_SEC = 10
