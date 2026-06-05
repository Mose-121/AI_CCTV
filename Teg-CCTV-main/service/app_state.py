"""
app_state.py — Shared mutable state for the application.

All global variables that were previously scattered as module-level globals
in server.py are consolidated here for clean dependency injection.

NOTE: No heavy imports at module level (e.g. Database) — those are set during lifespan.
"""

import os
import threading
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import WebSocket

# ──────────────────────────────────────────────
#  Core objects (set during lifespan startup)
# ──────────────────────────────────────────────
db: Any = None  # Will be set to Database() instance during startup

# Each entry: (worker, thread, frame_q, log_q, status_q, recorder)
workers: List[tuple] = []

# ──────────────────────────────────────────────
#  Frame storage
# ──────────────────────────────────────────────
latest_frame: Dict[str, np.ndarray] = {}
latest_frame_sub: Dict[str, np.ndarray] = {}
latest_frame_ts: Dict[str, float] = {}
latest_lock = threading.Lock()

# ──────────────────────────────────────────────
#  Camera metadata & preview
# ──────────────────────────────────────────────
camera_meta_by_name: Dict[str, Dict[str, Any]] = {}
preview_mode: Dict[str, str] = {}
sub_preview_threads: Dict[str, tuple] = {}

# ──────────────────────────────────────────────
#  WebSocket subscribers (UI updates)
# ──────────────────────────────────────────────
event_subscribers: List[WebSocket] = []

# ──────────────────────────────────────────────
#  Camera health
# ──────────────────────────────────────────────
camera_last_known_status: Dict[str, str] = {}
camera_down_timestamp: Dict[str, float] = {}
health_monitor_lock = threading.Lock()

# ──────────────────────────────────────────────
#  Runtime settings (segment duration, etc.)
# ──────────────────────────────────────────────
runtime_settings: Dict[str, Any] = {
    "SEGMENT_MINUTES": int(os.getenv("SEGMENT_MINUTES", "15")),
}
runtime_settings_lock = threading.Lock()
