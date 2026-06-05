"""
config.py — Shared configuration, imports, and constants for the CCTV UI.
All modules should import from here instead of duplicating imports.
"""

# ─── Standard Library ─────────────────────────────────────────────
import sys
import os
import json
import time
import threading
import asyncio
import csv
import mimetypes
import re
import base64
import logging

from datetime import datetime, date
from typing import Optional, List, Tuple, Dict
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

# ─── Third Party ──────────────────────────────────────────────────
import requests
import cv2
import numpy as np
import websockets
import pytz

# ─── Qt Multimedia env (must be set before importing Qt) ──────────
os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation'

# ─── PyQt5 ────────────────────────────────────────────────────────
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import *
from PyQt5.QtMultimediaWidgets import *

# ─── Logging ──────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Application Config ──────────────────────────────────────────
CONFIG = {
    "SERVER_BASE": os.environ.get("SERVER_BASE", "http://192.168.1.104:8000"),
    "MAX_TILES": 9,
}

# ─── Paths ────────────────────────────────────────────────────────
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
ASSETS_DIR = os.path.join(APP_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")

# ─── Regex ────────────────────────────────────────────────────────
FILENAME_TIME_RE = re.compile(r'_(\d{2})[-_]?(\d{2})[-_]?(\d{2})(?:\.\w+)?$')
