"""
camera_dialogs.py — Add, Edit, Delete, and Select Camera dialogs.
"""
from config import *
from theme import *
from api_client import APIClient
from utils import build_rtsp_url, infer_rtsp_variants


# ══════════════════════════════════════════════════════════════════
#   Add Camera Dialog
# ══════════════════════════════════════════════════════════════════

class AddCameraDialog(QDialog):
    cameraAdded = pyqtSignal()

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Add Camera")
        self.setMinimumSize(560, 520)
        self.setStyleSheet(DIALOG_STYLESHEET)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)

        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        v = QVBoxLayout(wrap)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(10)

        # ── Header ────────────────────────────────────────────────
        header = QLabel()
        header.setText(styled_title("📹 Register New Camera"))
        header.setAlignment(Qt.AlignCenter)
        v.addWidget(header)
        v.addSpacing(8)

        # ── Form ──────────────────────────────────────────────────
        f = QFormLayout()
        f.setSpacing(10)
        f.setLabelAlignment(Qt.AlignRight)

        self.name_code = QLineEdit()
        self.name_code.setPlaceholderText("Camera Code / Display Name (e.g., B101-Front)")
        self.name_code.setFixedHeight(38)
        f.addRow("Camera Name:", self.name_code)

        self.brand = QComboBox()
        self.brand.addItems(["Generic", "Dahua", "Hikvision", "Uniview", "Axis", "Reolink", "Ezviz", "ONVIF-Generic"])
        f.addRow("Brand:", self.brand)

        self.host = QLineEdit()
        self.host.setPlaceholderText("e.g., 192.168.1.100")
        f.addRow("Host / IP:", self.host)

        self.port = QLineEdit()
        self.port.setPlaceholderText("554")
        self.port.setFixedWidth(100)
        f.addRow("Port:", self.port)

        self.user = QLineEdit()
        self.user.setPlaceholderText("Camera username")
        f.addRow("Username:", self.user)

        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.Password)
        self.pw.setPlaceholderText("Camera password")
        f.addRow("Password:", self.pw)

        self.channel = QLineEdit()
        self.channel.setText("1")
        self.channel.setFixedWidth(60)
        f.addRow("Channel:", self.channel)

        self.custom_path = QLineEdit()
        self.custom_path.setPlaceholderText("e.g., /h264_stream or /Streaming/Channels/101")
        f.addRow("Custom Path:", self.custom_path)

        self.zone = QComboBox()
        self.zone.addItems(["building", "car"])
        f.addRow("Zone:", self.zone)

        self.department = QComboBox()
        initial_depts = ["(พิมพ์เพื่อเพิ่ม)", "CENTER", "CONDO", "EQR", "TER", "OFFICE1-2&FIN",
                         "TETSO", "TEI", "EPO", "STORE", "TEBP", "R&D"]
        unique_depts = sorted(list(set(initial_depts) - {"(พิมพ์เพื่อเพิ่ม)"}))
        self.department.addItems(["(พิมพ์เพื่อเพิ่ม)"] + unique_depts)
        self.department.setEditable(True)
        self.department.lineEdit().setPlaceholderText("เลือกหรือพิมพ์แผนกใหม่...")
        self.department.currentTextChanged.connect(
            lambda t: self.department.lineEdit().setText("") if t == "(พิมพ์เพื่อเพิ่ม)" else None)
        f.addRow("Department:", self.department)

        # ── Preview URLs ──────────────────────────────────────────
        self.preview_url = QLineEdit()
        self.preview_url.setReadOnly(True)
        f.addRow("Main RTSP URL:", self.preview_url)

        self.preview_url2 = QLineEdit()
        self.preview_url2.setReadOnly(True)
        f.addRow("Sub RTSP URL:", self.preview_url2)

        v.addLayout(f)
        v.addSpacing(8)

        # ── Action Buttons ────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.btn_preview = QPushButton("🔍 Preview URL")
        self.btn_preview.setObjectName("secondaryBtn")
        self.btn_test = QPushButton("⚡ Test Stream")
        self.btn_test.setObjectName("secondaryBtn")
        btn_row.addWidget(self.btn_preview)
        btn_row.addWidget(self.btn_test)
        v.addLayout(btn_row)

        self.btn_add = QPushButton("✅ Add Camera")
        self.btn_add.setFixedHeight(44)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        v.addWidget(self.btn_add)

        # ── Help Tips ─────────────────────────────────────────────
        self.help = QLabel(
            "Tips: Dahua→channel=1 | Hikvision→101 per channel | Uniview→unicast\n"
            "Axis→resolution | Reolink→h264Preview | Generic→custom path"
        )
        self.help.setStyleSheet(f"color: {Colors.TEXT_DISABLED}; font-size: 11px; padding: 8px;")
        self.help.setWordWrap(True)
        v.addWidget(self.help)

        scroll.setWidget(wrap)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        self.msg = QLabel("")
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px; padding: 6px;")
        root.addWidget(self.msg)

        # ── Connections ───────────────────────────────────────────
        widgets = [self.brand, self.host, self.port, self.user, self.pw, self.channel, self.custom_path]
        for w in widgets:
            if isinstance(w, QComboBox): w.currentIndexChanged.connect(self.update_preview_url)
            else: w.textChanged.connect(self.update_preview_url)

        self.btn_preview.clicked.connect(self.update_preview_url)
        self.btn_test.clicked.connect(self.test_preview_url)
        self.btn_add.clicked.connect(self.submit)

        self.port.setText("554")
        self.channel.setText("1")
        self.apply_brand_visibility()
        self.brand.currentIndexChanged.connect(self.apply_brand_visibility)
        self.update_preview_url()

    def apply_brand_visibility(self):
        b = (self.brand.currentText() or "").lower()
        self.custom_path.setVisible(b == "generic")

    def update_preview_url(self):
        try:
            url = build_rtsp_url(
                self.brand.currentText(), self.host.text().strip(), self.port.text().strip(),
                self.user.text().strip(), self.pw.text().strip(), self.channel.text().strip(),
                "", "", "", self.custom_path.text().strip()
            )
            main, sub = infer_rtsp_variants(url)
            self.preview_url.setText(main)
            self.preview_url2.setText(sub)
        except Exception as e:
            logger.error(f"Error updating preview URL: {e}")
            self.preview_url.setText("")
            self.preview_url2.setText("")

    def test_preview_url(self):
        url = self.preview_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Test URL", "No RTSP URL provided")
            return
        self.btn_test.setEnabled(False)
        self.btn_test.setText("⏳ Testing...")
        QApplication.processEvents()
        ok = False
        try:
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            t0 = time.time()
            while time.time() - t0 < 2.0:
                ret, _ = cap.read()
                if ret: ok = True; break
                time.sleep(0.05)
            cap.release()
        except Exception as e:
            logger.error(f"RTSP test failed: {e}")
        finally:
            self.btn_test.setEnabled(True)
            self.btn_test.setText("⚡ Test Stream")
        QMessageBox.information(self, "Test Result",
                                "✅ Stream opened successfully!" if ok else "❌ Failed to open stream")

    def submit(self):
        name = self.name_code.text().strip()
        url = self.preview_url.text().strip()
        url2 = self.preview_url2.text().strip()
        zone = self.zone.currentText()
        comp = self.department.currentText().strip() if self.department.currentText().strip() else None
        if not name or not url:
            QMessageBox.warning(self, "ข้อมูลไม่ครบ", "กรุณากรอกชื่อกล้องและ RTSP URL")
            return
        try:
            self.api.add_camera("", name, url, zone, comp, url2=url2)
            QMessageBox.information(self, "✅ สำเร็จ", "เพิ่มกล้องเรียบร้อยแล้ว!")
            self.cameraAdded.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "❌ เกิดข้อผิดพลาด", f"Failed to add camera:\n{str(e)}")


# ══════════════════════════════════════════════════════════════════
#   Edit Camera Dialog
# ══════════════════════════════════════════════════════════════════

class EditCameraDialog(QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Edit Camera")
        self.setFixedSize(500, 440)
        self.setStyleSheet(DIALOG_STYLESHEET)

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 20, 28, 20)
        v.setSpacing(10)

        header = QLabel()
        header.setText(styled_title("✏️ Edit Camera Settings"))
        header.setAlignment(Qt.AlignCenter)
        v.addWidget(header)
        v.addSpacing(8)

        f = QFormLayout()
        f.setSpacing(10)

        try:
            self.cameras = self.api.list_cameras()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load cameras: {e}")
            self.cameras = []

        self.cam_cb = QComboBox()
        for cam in self.cameras:
            code = cam.get("camera_name", "")
            self.cam_cb.addItem(f"{code}", cam)
        f.addRow("Select Camera:", self.cam_cb)

        self.url = QLineEdit()
        f.addRow("RTSP URL (Main):", self.url)

        self.url2 = QLineEdit()
        f.addRow("RTSP URL (Sub):", self.url2)

        self.zone = QComboBox()
        self.zone.addItems(["face", "car"])
        f.addRow("Zone:", self.zone)

        self.department = QComboBox()
        initial_depts = ["(พิมพ์เพื่อเพิ่ม)", "CENTER", "CONDO", "EPO", "EQR", "OFFICE1-2&FIN",
                         "R&D", "TETSO", "TEBP", "TEI", "TER"]
        unique_depts = sorted(list(set(initial_depts) - {"(พิมพ์เพื่อเพิ่ม)"}))
        self.department.addItems(["(พิมพ์เพื่อเพิ่ม)"] + unique_depts)
        self.department.setEditable(True)
        self.department.lineEdit().setPlaceholderText("เลือกหรือพิมพ์แผนกใหม่...")
        self.department.currentTextChanged.connect(
            lambda t: self.department.lineEdit().setText("") if t == "(พิมพ์เพื่อเพิ่ม)" else None)
        f.addRow("Department:", self.department)

        v.addLayout(f)
        v.addSpacing(12)

        self.msg = QLabel("")
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
        v.addWidget(self.msg)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.setStyleSheet(f"""
            QDialogButtonBox QPushButton {{
                min-width: 100px;
                padding: 10px 20px;
            }}
        """)
        btns.accepted.connect(self.handle_save)
        btns.rejected.connect(self.reject)
        v.addWidget(btns)

        self.cam_cb.currentIndexChanged.connect(self.populate_fields)
        if self.cameras: self.populate_fields(0)

    def populate_fields(self, idx):
        cam = self.cam_cb.itemData(idx)
        if not cam: return
        self.url.setText(cam.get("url", ""))
        self.url2.setText(cam.get("url2", ""))
        self.zone.setCurrentText(cam.get("zone", "face") or "face")
        self.department.setCurrentText(cam.get("department", "") or "")

    def handle_save(self):
        idx = self.cam_cb.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "ผิดพลาด", "กรุณาเลือกกล้องที่ต้องการแก้ไข")
            return
        cam_data = self.cam_cb.itemData(idx)
        if not cam_data:
            QMessageBox.critical(self, "ผิดพลาด", "ไม่สามารถดึงข้อมูลกล้องได้")
            return
        code = cam_data.get("camera_name")
        if not code:
            QMessageBox.critical(self, "ผิดพลาด", "ไม่พบ Camera Name/Code")
            return
        url = self.url.text().strip()
        url2 = self.url2.text().strip()
        zone = self.zone.currentText()
        comp = self.department.currentText().strip()
        if comp == "(พิมพ์เพื่อเพิ่ม)" or not comp: comp = None
        try:
            self.api.update_camera(code, url=url, zone=zone, comp=comp)
            QMessageBox.information(self, "สำเร็จ", "แก้ไขกล้องเรียบร้อย")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "เกิดข้อผิดพลาด", f"Failed to update camera: {str(e)}")


# ══════════════════════════════════════════════════════════════════
#   Delete Camera Dialog
# ══════════════════════════════════════════════════════════════════

class DeleteCameraDialog(QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Delete Camera")
        self.setFixedSize(380, 220)
        self.setStyleSheet(DIALOG_STYLESHEET)

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 20, 28, 20)
        v.setSpacing(12)

        header = QLabel()
        header.setText(styled_title("⚠️ Delete Camera"))
        header.setAlignment(Qt.AlignCenter)
        v.addWidget(header)

        desc = QLabel("เมื่อลบแล้วจะไม่สามารถกู้คืนได้ กรุณาตรวจสอบให้แน่ใจ")
        desc.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        v.addWidget(desc)
        v.addSpacing(4)

        form = QFormLayout()
        self.camera_code = QLineEdit()
        self.camera_code.setPlaceholderText("Camera code (camera_name)")
        self.camera_code.setFixedHeight(40)
        form.addRow("Camera Code:", self.camera_code)
        v.addLayout(form)

        self.btn = QPushButton("🗑️ Delete Camera")
        self.btn.setObjectName("dangerBtn")
        self.btn.setFixedHeight(42)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self.handle_delete)
        v.addWidget(self.btn)

        self.msg = QLabel("")
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
        v.addWidget(self.msg)

    def handle_delete(self):
        code = self.camera_code.text().strip()
        if not code: self.msg.setText("Please enter camera code"); return
        try:
            self.api.delete_camera(code)
            QMessageBox.information(self, "Success", f"Camera {code} deleted successfully")
            self.accept()
        except Exception as e:
            self.msg.setText(f"Error: {e}")


# ══════════════════════════════════════════════════════════════════
#   Select Camera Dialog (for Recordings)
# ══════════════════════════════════════════════════════════════════

class SelectCameraDialog(QDialog):
    def __init__(self, cameras, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Camera for Recordings")
        self.setMinimumSize(440, 520)
        self.setStyleSheet(DIALOG_STYLESHEET)

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(10)

        header = QLabel()
        header.setText(styled_title("📹 Select Camera"))
        header.setAlignment(Qt.AlignCenter)
        v.addWidget(header)
        v.addSpacing(4)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Search by camera code or name...")
        self.search.setFixedHeight(40)
        v.addWidget(self.search)

        self.listw = QListWidget()
        v.addWidget(self.listw, 1)

        self.cameras = cameras
        self.filtered = cameras
        self.populate_list()
        self.search.textChanged.connect(self.on_search)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        v.addWidget(btns)

    def on_search(self, text):
        t = text.strip().lower()
        if not t: self.filtered = self.cameras
        else:
            self.filtered = [
                cam for cam in self.cameras
                if t in (cam.get("camera_code", "") or cam.get("camera_name", "")).lower()
                or t in cam.get("camera_name", "").lower()
            ]
        self.populate_list()

    def populate_list(self):
        self.listw.clear()
        for cam in self.filtered:
            label = f"{cam.get('camera_code', cam.get('camera_name'))} | {cam.get('camera_name')}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, cam)
            self.listw.addItem(item)

    def get_selected_camera(self):
        it = self.listw.currentItem()
        return it.data(Qt.UserRole) if it else None
