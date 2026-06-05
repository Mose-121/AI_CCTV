"""
api_client.py — API Client, WebSocket clients for the CCTV system.
"""
from config import *


class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.department = ""
        self.access = []
        self.is_admin = False
        self.username = ""

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"token": self.token, "user": self.username}, f)
        except Exception:
            pass

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return None
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.token = data.get("token")
                self.username = data.get("user") or ""
                return data
        except Exception:
            return None

    def clear_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
        except Exception:
            pass

    def _headers(self):
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, path, params=None, stream=False):
        url = self.base_url + path
        return requests.get(url, headers=self._headers(), params=params, timeout=(8, 25), stream=stream)

    def _post(self, path, json=None, data=None, files=None, stream=False):
        url = self.base_url + path
        return requests.post(url, headers=self._headers(), json=json, data=data, files=files, timeout=(8, 25), stream=stream)

    def _put(self, path, json=None):
        url = self.base_url + path
        return requests.put(url, headers=self._headers(), json=json, timeout=(8, 25))

    def _delete(self, path):
        url = self.base_url + path
        return requests.delete(url, headers=self._headers(), timeout=(8, 25))

    def login(self, username: str, password: str, remember: bool = False, force: bool = False) -> dict:
        params = {}
        if remember: params["remember"] = "true"
        if force: params["force"] = "true"
        url = self.base_url + "/auth/login"
        r = requests.post(url, headers=self._headers(),
                          json={"username": username, "password": password},
                          params=params or None, timeout=(8, 25))
        if r.status_code != 200:
            if "application/json" in (r.headers.get("content-type") or ""):
                detail = r.json().get("detail")
            else:
                detail = r.text
            raise RuntimeError(f"{r.status_code} {detail or 'Unauthorized'}")
        js = r.json()
        self.token = js.get("access_token")
        self.department = js.get("department", "")
        self.access = js.get("access", [])
        self.is_admin = bool(js.get("is_admin"))
        self.username = username
        return js

    def login_temp(self, username: str, temp_password: str) -> dict:
        r = self._post("/auth/login-temp", json={"username": username, "temp_password": temp_password})
        if r.status_code != 200:
            try: msg = r.json().get("detail")
            except Exception: msg = r.text
            raise RuntimeError(f"Temp login failed: {msg}")
        js = r.json()
        self.token = js.get("access_token")
        self.username = username
        self.department, self.access, self.is_admin = "", [], False
        return js

    def change_password(self, new_password: str) -> dict:
        r = self._post("/auth/change-password", json={"new_password": new_password})
        if r.status_code != 200:
            try: msg = r.json().get("detail")
            except Exception: msg = r.text
            raise RuntimeError(f"Change password failed: {msg}")
        js = r.json()
        self.token = js.get("access_token")
        self.department = js.get("department", "")
        self.access = js.get("access", [])
        self.is_admin = bool(js.get("is_admin", False))
        return js

    def logout(self):
        if not self.token:
            self.clear_config()
            self.department = ""
            self.access = []
            self.is_admin = False
            return
        try:
            self._post("/auth/logout", json={})
        except Exception:
            pass
        finally:
            self.token = None
            self.department = ""
            self.access = []
            self.is_admin = False
            self.clear_config()

    # ── Cameras ───────────────────────────────────────────────────
    def list_cameras(self) -> List[dict]:
        r = self._get("/cameras"); r.raise_for_status()
        cameras = r.json()
        for c in cameras:
            if "camera_code" not in c:
                c["camera_code"] = c.get("camera_name")
        return cameras

    def get_preview_mode(self, camera_name: str) -> dict:
        r = self._get(f"/cameras/{camera_name}/preview-mode")
        if r.status_code != 200:
            try: msg = r.json().get("detail")
            except Exception: msg = r.text
            raise RuntimeError(f"Get preview mode failed: {msg}")
        return r.json()

    def set_preview_mode(self, camera_name: str, mode: str) -> bool:
        r = self._post(f"/cameras/{camera_name}/preview-mode", json={"mode": mode})
        return r.status_code == 200

    def add_camera(self, code: str, name: str, url: str, zone: str,
                   comp: Optional[str] = None, url2: Optional[str] = None) -> dict:
        body = {"camera_name": code or name, "url": url, "zone": zone,
                "comp": comp or None, "url2": url2 or None}
        body = {k: v for k, v in body.items() if v is not None}
        r = self._post("/cameras", json=body)
        if r.status_code not in (200, 201):
            try: msg = r.json().get("detail")
            except Exception: msg = r.text
            raise RuntimeError(f"Add camera failed: {msg}")
        return r.json()

    def update_camera(self, code: str, url: Optional[str] = None, zone: Optional[str] = None,
                      comp: Optional[str] = None, url2: Optional[str] = None) -> dict:
        body = {}
        if url is not None: body["url"] = url
        if url2 is not None: body["url2"] = url2
        if zone is not None: body["zone"] = zone
        if comp is not None: body["comp"] = comp
        if not body: return {"ok": True}
        r = self._put(f"/cameras/{code}", json=body)
        if r.status_code != 200:
            try: msg = r.json().get("detail")
            except Exception: msg = r.text
            raise RuntimeError(f"Update camera failed: {msg}")
        return r.json()

    def delete_camera(self, code: str) -> dict:
        r = self._delete(f"/cameras/{code}")
        if r.status_code != 200:
            try: msg = r.json().get("detail")
            except Exception: msg = r.text
            raise RuntimeError(f"Delete camera failed: {msg}")
        return r.json()

    # ── Employees ─────────────────────────────────────────────────
    def list_employees(self) -> List[dict]:
        try:
            r = self._get("/employees"); r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Failed to list employees: {e}")
            raise RuntimeError(f"Failed to list employees: {e}")

    def get_employee_details(self, emp_id: str) -> dict:
        try:
            r = self._get(f"/employees/{emp_id}"); r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Failed to get employee details for {emp_id}: {e}")
            raise RuntimeError(f"Failed to get details: {e}")

    def delete_employee_slot(self, emp_id: str, slot_num: int) -> dict:
        try:
            r = self._delete(f"/employees/{emp_id}/slot/{slot_num}"); r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Failed to delete slot {slot_num} for {emp_id}: {e}")
            raise RuntimeError(f"Failed to delete slot: {e}")

    def update_employee_info(self, emp_id: str, name: str, department: str) -> dict:
        try:
            payload = {"name": name, "department": department}
            r = self._put(f"/employees/{emp_id}/info", json=payload); r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Failed to update info for {emp_id}: {e}")
            raise RuntimeError(f"Failed to update info: {e}")

    def update_employee(self, emp_id: str, name: Optional[str] = None,
                        department: Optional[str] = None,
                        image_paths: Optional[List[str]] = None) -> dict:
        if not emp_id:
            raise RuntimeError("Employee ID is required for update.")
        if not image_paths:
            raise RuntimeError("Please select one new image to add.")
        data = {}
        if name is not None: data["name"] = name
        if department is not None: data["department"] = department
        files = []
        path = image_paths[0]
        if not os.path.exists(path):
            raise RuntimeError(f"Image file not found: {path}")
        mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f: content = f.read()
        files.append(("files", (os.path.basename(path), content, mime)))
        r = self._post(f"/employees/{emp_id}/update", data=data, files=files)
        if r.status_code != 200:
            try: msg = r.json().get("detail")
            except Exception: msg = r.text
            raise RuntimeError(f"Update employee failed: {msg}")
        return r.json()

    def enroll_employee(self, emp_id: str, name: str, department: str, image_paths: List[str]) -> dict:
        if not image_paths:
            raise RuntimeError("No image selected")
        files = []
        for path in image_paths:
            if not os.path.exists(path):
                raise RuntimeError(f"Image file not found: {path}")
            if not path.lower().endswith((".jpg", ".jpeg", ".png")):
                raise RuntimeError("Please select a valid image file (.jpg, .jpeg, .png)")
            if os.path.getsize(path) / (1024 * 1024) > 10:
                raise RuntimeError("Image file is too large (max 10MB)")
            mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
            with open(path, "rb") as f: content = f.read()
            files.append(("files", (os.path.basename(path), content, mime)))
        data = {"emp_id": emp_id, "name": name, "department": department}
        r = self._post("/employees/enroll", data=data, files=files)
        if r.status_code not in (200, 201):
            msg = r.json().get("detail") if "application/json" in r.headers.get("content-type", "") else r.text
            if r.status_code == 500: msg = f"Server error: {msg}. Please check server logs."
            elif r.status_code == 400: msg = f"Invalid image: {msg}"
            elif r.status_code == 422: msg = f"No face found in image: {msg}"
            raise RuntimeError(msg)
        return r.json()

    def delete_employee(self, emp_id: str) -> dict:
        r = self._delete(f"/employees/{emp_id}")
        if r.status_code != 200:
            try: msg = r.json().get("detail")
            except Exception: msg = r.text
            raise RuntimeError(f"Delete employee failed: {msg}")
        return r.json()

    # ── Users / Reports / Admin ───────────────────────────────────
    def register_user(self, username: str, password: str, department: str, access: List[str], is_admin: bool) -> dict:
        body = {
            "user_name": username, "pass_user": password, "department": department,
            "access": access if isinstance(access, list) else [s.strip() for s in str(access or "").split(",") if s.strip()],
            "is_admin": bool(is_admin),
        }
        r = self._post("/users/register", json=body)
        if r.status_code != 200:
            try: msg = r.json().get("detail")
            except Exception: msg = r.text
            raise RuntimeError(f"Register failed: {msg}")
        return r.json()

    def list_reports(self, start=None, end=None, type_=None, department=None, q=None, limit=500) -> dict:
        params = {"limit": limit}
        if start: params["start"] = start
        if end: params["end"] = end
        if type_: params["type"] = type_
        if department is not None: params["department"] = department
        if q: params["q"] = q
        r = self._get("/reports", params=params)
        if r.status_code != 200:
            error_msg = r.json().get("detail") if "application/json" in r.headers.get("content-type", "") else r.text
            raise RuntimeError(error_msg)
        return r.json()

    def get_detections_for_file(self, filename: str, camera: str, zone: str, date: str) -> List[dict]:
        params = {"filename": filename, "camera": camera, "zone": zone, "date": date}
        try:
            r = self._get("/reports/by-video-file", params=params); r.raise_for_status()
            return r.json().get("items", [])
        except Exception as e:
            logger.error(f"Failed to get detections for {filename}: {e}")
            raise RuntimeError(f"API Error: {str(e)}")

    def list_recordings(self, camera_name: str, zone: str, date: Optional[str] = None,
                        person_name: Optional[str] = None) -> List[dict]:
        params = {}
        if camera_name: params["camera"] = camera_name
        if zone: params["zone"] = zone
        if date: params["date"] = date
        if person_name and person_name.strip():
            params["person_name"] = person_name.strip()
        try:
            r = self._get("/recordings", params=params); r.raise_for_status()
            items = r.json()
        except Exception as e:
            logger.error(f"list_recordings failed: {e}")
            items = []

        def _build_display_name(it) -> str:
            cam = camera_name or it.get("camera") or ""
            date_raw = it.get("date") or ""
            try:
                dt = datetime.strptime(date_raw, "%Y-%m-%d")
                dmy = dt.strftime("%d%m%Y")
            except Exception:
                dmy = date_raw.replace("-", "")
            fn = (it.get("file") or it.get("filename") or "")
            m = re.search(r'(?<!\d)(\d{2})[-_]?(\d{2})[-_]?(\d{2})(?!\d)', fn)
            if m:
                hms = "".join(m.groups())
            else:
                mod = it.get("modified") or ""
                hms = mod.split("T")[1][:8].replace(":", "") if "T" in mod else ""
            parts = [cam]
            if dmy: parts.append(dmy)
            if hms: parts.append(hms)
            return "_".join(parts)

        out = []
        for it in items:
            size_bytes = it.get("size_bytes", 0) or 0
            out.append({
                "file": it.get("file") or it.get("filename"),
                "modified": it.get("modified"),
                "department": it.get("department"),
                "zone": it.get("zone"),
                "camera": it.get("camera"),
                "date": it.get("date"),
                "size_bytes": size_bytes,
                "size_mb": round(float(size_bytes) / (1024 * 1024), 2),
                "display_name": _build_display_name(it),
            })
        return out

    def download_recording(self, department: str, zone: str, camera_name: str, filename: str, save_path: str, date: Optional[str] = None):
        if date:
            path = f"/recordings/{department}/{zone}/{camera_name}/{date}/{filename}"
        else:
            path = f"/recordings/{department}/{zone}/{camera_name}/{filename}"
        r = self._get(path, stream=True)
        if r.status_code == 404 and date:
            r = self._get(f"/recordings/{department}/{zone}/{camera_name}/{filename}", stream=True)
        r.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk: f.write(chunk)

    def mjpg_ws_url(self, camera_name: str) -> str:
        u = urlparse(self.base_url)
        scheme = "wss" if u.scheme == "https" else "ws"
        path = f"/ws/mjpg/{camera_name}"
        qs = urlencode({"token": self.token or ""})
        return urlunparse((scheme, u.netloc, path, "", qs, ""))

    def admin_reset_temp_password(self, username: str, expire_minutes: int = 30, temp_password: Optional[str] = None) -> dict:
        if not username: raise RuntimeError("Username is required")
        body = {"expire_minutes": int(expire_minutes)}
        if temp_password: body["temp_password"] = temp_password
        r = self._post(f"/admin/users/{username}/reset-password-temp", json=body)
        if r.status_code != 200:
            try: msg = r.json().get("detail")
            except Exception: msg = r.text
            raise RuntimeError(f"Reset temp password failed: {msg}")
        return r.json()

    def set_segment_minutes(self, minutes: int) -> dict:
        if minutes < 1 or minutes > 120:
            raise RuntimeError("Segment time must be between 1 and 120 minutes.")
        r = self._post("/admin/settings/segment", json={"minutes": minutes})
        if r.status_code != 200:
            try: msg = r.json().get("detail")
            except Exception: msg = r.text
            raise RuntimeError(f"Failed to set segment time: {msg}")
        return r.json()

    def get_camera_events(self, start_date: str, end_date: str) -> List[dict]:
        params = {"start": start_date, "end": end_date}
        try:
            r = self._get("/reports/camera-events", params=params); r.raise_for_status()
            return r.json().get("items", [])
        except Exception as e:
            logger.error(f"Failed to get camera events: {e}")
            raise RuntimeError(f"Failed to get events: {e}")


# ══════════════════════════════════════════════════════════════════
#   UI WebSocket Client (real-time health status)
# ══════════════════════════════════════════════════════════════════

class UIWebSocketClient(QObject):
    status_updated = pyqtSignal(dict)
    connection_lost = pyqtSignal(str)

    def __init__(self, api: APIClient):
        super().__init__()
        self.api = api
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self):
        if self._thread and self._thread.is_alive(): return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        t = self._thread
        self._thread = None
        if t and t.is_alive():
            try: t.join(timeout=1.0)
            except Exception: pass

    def _build_url(self) -> str:
        u = urlparse(self.api.base_url)
        scheme = "wss" if u.scheme == "https" else "ws"
        qs = urlencode({"token": self.api.token or ""})
        return urlunparse((scheme, u.netloc, "/ws/ui-updates", "", qs, ""))

    def _run_loop(self):
        try:
            asyncio.run(self._ws_main())
        except Exception as e:
            logger.error(f"UI WS loop error: {e}")
            self.connection_lost.emit(f"WebSocket loop error: {e}")

    async def _ws_main(self):
        url = self._build_url()
        logger.info(f"Connecting UI WS: {url}")
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                logger.info("[UI WS] Connected successfully.")
                self.connection_lost.emit("")
                while not self._stop.is_set():
                    try:
                        msg_str = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(msg_str)
                        if data.get("type") == "health_status":
                            self.status_updated.emit(data.get("data", {}))
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.warning(f"[UI WS] Message error: {e}")
        except Exception as e:
            logger.error(f"[UI WS] Connection failed: {e}")
            self.connection_lost.emit(f"Connection failed: {e}")
            time.sleep(5)


# ══════════════════════════════════════════════════════════════════
#   MJPEG over WebSocket Player
# ══════════════════════════════════════════════════════════════════

class MJPGWebSocketPlayer:
    def __init__(self, api: APIClient, camera_name: str, on_frame_cb):
        self.api = api
        self.camera_name = camera_name
        self.on_frame_cb = on_frame_cb
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self):
        if self._thread and self._thread.is_alive(): return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        t = self._thread
        self._thread = None
        if t and t.is_alive():
            try: t.join(timeout=2.0)
            except Exception: pass

    def _run_loop(self):
        try:
            asyncio.run(self._ws_main())
        except Exception as e:
            logger.error(f"MJPG ws loop error: {e}")
            self.on_frame_cb(None, f"WebSocket error: {e}")

    @staticmethod
    def _extract_jpeg(payload: bytes) -> Optional[bytes]:
        try:
            sep = payload.find(b"\r\n\r\n")
            if sep == -1: return None
            header = payload[:sep]
            body = payload[sep + 4:]
            clen = None
            for line in header.split(b"\r\n"):
                if line.lower().startswith(b"content-length:"):
                    try: clen = int(line.split(b":", 1)[1].strip())
                    except Exception: clen = None
                    break
            if clen is None: return body
            if len(body) < clen: return None
            return body[:clen]
        except Exception:
            return None

    async def _ws_main(self):
        url = self.api.mjpg_ws_url(self.camera_name)
        logger.info(f"Connecting MJPG WS: {url}")
        try:
            async with websockets.connect(url, max_size=None, ping_interval=20, ping_timeout=20) as ws:
                while not self._stop.is_set():
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30)
                    except asyncio.TimeoutError:
                        continue
                    if isinstance(msg, (bytes, bytearray)):
                        jpeg = self._extract_jpeg(msg)
                        if not jpeg: continue
                        arr = np.frombuffer(jpeg, np.uint8)
                        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                        if bgr is None: continue
                        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                        self.on_frame_cb(rgb, None)
                    else:
                        try: self.on_frame_cb(None, str(msg))
                        except Exception: pass
        except Exception as e:
            self.on_frame_cb(None, f"WS connect error: {e}")
