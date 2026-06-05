"""
admin_dialogs.py — Admin Hub, Reports, Recordings, Camera Event Log.
"""
from config import *
from theme import *
from utils import _parse_video_start_time
from api_client import APIClient
from components import YouTubeLikePlayer
from auth_dialogs import RegisterDialog, ResetTempPasswordDialog


# ══════════════════════════════════════════════════════════════════
#   Admin Hub — Card Grid
# ══════════════════════════════════════════════════════════════════

class AdminHub(QDialog):
    def __init__(self, api: APIClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Admin Tools")
        self.setMinimumSize(560, 540)
        self.setStyleSheet(ADMIN_HUB_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # ── Header ────────────────────────────────────────────────
        header = QLabel()
        header.setText(styled_title("⚙️ Administrative Tools", 20))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        subtitle = QLabel("Manage users, employees, cameras and system settings")
        subtitle.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(12)

        def card(text, desc, icon_enum):
            btn = QPushButton()
            btn.setObjectName("adminCard")
            btn.setMinimumHeight(78)
            btn.setCursor(Qt.PointingHandCursor)
            row = QHBoxLayout(btn)
            row.setContentsMargins(14, 10, 14, 10)
            row.setSpacing(14)

            icon_label = QLabel()
            icon_label.setPixmap(self.style().standardIcon(icon_enum).pixmap(QSize(28, 28)))
            icon_label.setFixedSize(40, 40)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet(f"""
                background: {Colors.PRIMARY_BG};
                border-radius: 10px;
                border: 1px solid rgba(0,180,216,0.15);
            """)

            text_w = QWidget()
            text_w.setAttribute(Qt.WA_TranslucentBackground)
            vl = QVBoxLayout(text_w)
            vl.setContentsMargins(0, 0, 0, 0)
            vl.setSpacing(2)
            t = QLabel(text)
            t.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {Colors.TEXT_PRIMARY}; background: transparent;")
            d = QLabel(desc)
            d.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY}; background: transparent;")
            vl.addWidget(t)
            vl.addWidget(d)

            row.addWidget(icon_label, 0, Qt.AlignLeft)
            row.addWidget(text_w, 1, Qt.AlignLeft)
            return btn

        self.btn_register  = card("Register User",    "Create a new user account",     QStyle.SP_DialogYesButton)
        self.btn_addemp    = card("Enroll Employee",   "Add employee for face recognition", QStyle.SP_FileIcon)
        self.btn_editemp   = card("Edit Employee",     "Update name, department, photos",   QStyle.SP_FileLinkIcon)
        self.btn_delemp    = card("Delete Employee",   "Remove employee from system",       QStyle.SP_TrashIcon)
        self.btn_addcam    = card("Add Camera",        "Register new camera stream",        QStyle.SP_DesktopIcon)
        self.btn_editcam   = card("Edit Camera",       "Modify existing camera settings",   QStyle.SP_FileDialogStart)
        self.btn_delcam    = card("Delete Camera",     "Remove a camera from the system",   QStyle.SP_DialogCancelButton)
        self.btn_temp      = card("Temp Password",     "Generate a temporary login password", QStyle.SP_MessageBoxWarning)
        self.btn_event_log = card("Event Log",         "View camera status history (OK/DOWN)", QStyle.SP_FileDialogDetailedView)

        grid.addWidget(self.btn_register,  0, 0)
        grid.addWidget(self.btn_temp,      0, 1)
        grid.addWidget(self.btn_addemp,    1, 0)
        grid.addWidget(self.btn_editemp,   1, 1)
        grid.addWidget(self.btn_delemp,    2, 0)
        grid.addWidget(self.btn_addcam,    2, 1)
        grid.addWidget(self.btn_editcam,   3, 0)
        grid.addWidget(self.btn_delcam,    3, 1)
        grid.addWidget(self.btn_event_log, 4, 0)
        layout.addLayout(grid)
        layout.addStretch()

        # ── Drop shadows on cards ─────────────────────────────────
        for btn in [self.btn_register, self.btn_temp, self.btn_addemp, self.btn_editemp,
                    self.btn_delemp, self.btn_addcam, self.btn_editcam, self.btn_delcam,
                    self.btn_event_log]:
            apply_shadow(btn, blur=14, offset_y=3, color=Colors.SHADOW_SOFT)

        # ── Lazy imports to avoid circular deps ───────────────────
        from employee_dialogs import AddEmployeeDialog, DeleteEmployeeDialog, EditEmployeeDialog
        from camera_dialogs import AddCameraDialog, EditCameraDialog, DeleteCameraDialog

        self.btn_register.clicked.connect(lambda: RegisterDialog(self.api, self).exec_())
        self.btn_addemp.clicked.connect(lambda: AddEmployeeDialog(self.api, self).exec_())
        self.btn_delemp.clicked.connect(lambda: DeleteEmployeeDialog(self.api, self).exec_())
        self.btn_editemp.clicked.connect(lambda: EditEmployeeDialog(self.api, self).exec_())
        self.btn_addcam.clicked.connect(lambda: AddCameraDialog(self.api, self).exec_())
        self.btn_editcam.clicked.connect(lambda: EditCameraDialog(self.api, self).exec_())
        self.btn_delcam.clicked.connect(lambda: DeleteCameraDialog(self.api, self).exec_())
        self.btn_temp.clicked.connect(lambda: ResetTempPasswordDialog(self.api, self).exec_())
        self.btn_event_log.clicked.connect(lambda: CameraEventLogDialog(self.api, self).exec_())

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=300)


# ══════════════════════════════════════════════════════════════════
#   Camera Event Log Dialog
# ══════════════════════════════════════════════════════════════════

class CameraEventLogDialog(QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Camera Status Event Log")
        self.setMinimumSize(820, 540)
        self.setStyleSheet(DIALOG_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QLabel()
        header.setText(styled_title("📋 Camera Event Log"))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        layout.addSpacing(4)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Start Date:"))
        self.start_date = QDateEdit(QDate.currentDate().addDays(-7))
        self.start_date.setCalendarPopup(True)
        self.start_date.setFixedWidth(140)
        ctrl.addWidget(self.start_date)
        ctrl.addWidget(QLabel("End Date:"))
        self.end_date = QDateEdit(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setFixedWidth(140)
        ctrl.addWidget(self.end_date)
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setObjectName("secondaryBtn")
        self.btn_refresh.clicked.connect(self.fetch_events)
        ctrl.addWidget(self.btn_refresh)
        ctrl.addStretch(1)
        layout.addLayout(ctrl)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Event Time", "Camera Name", "Status"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        QTimer.singleShot(50, self.fetch_events)

    def fetch_events(self):
        start_str = self.start_date.date().toString("yyyy-MM-dd")
        end_str = self.end_date.date().toString("yyyy-MM-dd")
        try:
            self.btn_refresh.setText("⏳ Loading...")
            QApplication.processEvents()
            events = self.api.get_camera_events(start_str, end_str)
            self.table.setSortingEnabled(False)
            self.table.setRowCount(0)
            for row, item in enumerate(events):
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(item.get('time_str', '')))
                self.table.setItem(row, 1, QTableWidgetItem(item.get('camera_name', '')))
                status_str = item.get('status', 'N/A')
                status_item = QTableWidgetItem(status_str)
                if status_str == "DOWN":
                    status_item.setForeground(QColor(Colors.DANGER))
                elif status_str == "OK":
                    status_item.setForeground(QColor(Colors.SUCCESS))
                else:
                    status_item.setForeground(QColor(Colors.TEXT_DISABLED))
                self.table.setItem(row, 2, status_item)
            self.table.setSortingEnabled(True)
            self.table.sortItems(0, Qt.DescendingOrder)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load events:\n{str(e)}")
        finally:
            self.btn_refresh.setText("🔄 Refresh")


# ══════════════════════════════════════════════════════════════════
#   Reports Dialog
# ══════════════════════════════════════════════════════════════════

class ReportsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 Reports (Face / Car)")
        self.setMinimumSize(1020, 680)
        self.setStyleSheet(DIALOG_STYLESHEET)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        header = QLabel()
        header.setText(styled_title("📊 Detection Reports"))
        header.setAlignment(Qt.AlignCenter)
        root.addWidget(header)
        root.addSpacing(4)

        # ── Quick Time Filters ────────────────────────────────────
        quick = QHBoxLayout()
        self.btn_today = QPushButton("Today")
        self.btn_today.setObjectName("secondaryBtn")
        self.btn_24h = QPushButton("Last 24h")
        self.btn_24h.setObjectName("secondaryBtn")
        self.btn_7d = QPushButton("Last 7d")
        self.btn_7d.setObjectName("secondaryBtn")
        for b in (self.btn_today, self.btn_24h, self.btn_7d):
            b.setFixedHeight(30)
            b.setCursor(Qt.PointingHandCursor)
            quick.addWidget(b)
        quick.addStretch(1)
        root.addLayout(quick)

        # ── Search Form ───────────────────────────────────────────
        form = QFormLayout()
        form.setSpacing(8)

        self.start_dt = QDateTimeEdit()
        self.start_dt.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_dt.setCalendarPopup(True)
        self.start_dt.setDateTime(QDateTime(QDate.currentDate(), QTime(0, 0, 0)))
        form.addRow("Start:", self.start_dt)

        self.end_dt = QDateTimeEdit()
        self.end_dt.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_dt.setCalendarPopup(True)
        self.end_dt.setDateTime(QDateTime.currentDateTime())
        form.addRow("End:", self.end_dt)

        self.dept_cb = QComboBox()
        self.dept_cb.setEditable(False)
        self._populate_departments()
        form.addRow("Department:", self.dept_cb)

        self.type_cb = QComboBox()
        self.type_cb.addItems(["ทั้งหมด", "Face", "Car"])
        form.addRow("Type:", self.type_cb)

        self.camera_code = QLineEdit()
        self.camera_code.setPlaceholderText("e.g., CAM01 (optional)")
        form.addRow("Camera:", self.camera_code)

        self.q_line = QLineEdit()
        self.q_line.setPlaceholderText("🔍 Search: name / plate / department / province / status")
        form.addRow("Search:", self.q_line)

        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 5000)
        self.limit_spin.setValue(500)
        form.addRow("Row Limit:", self.limit_spin)

        root.addLayout(form)

        # ── Actions ───────────────────────────────────────────────
        actions = QHBoxLayout()
        self.btn_refresh = QPushButton("🔎 Search / Refresh")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_export = QPushButton("📁 Export CSV")
        self.btn_export.setObjectName("secondaryBtn")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        actions.addWidget(self.btn_refresh)
        actions.addStretch(1)
        actions.addWidget(self.btn_export)
        root.addLayout(actions)

        # ── Summary Strip ─────────────────────────────────────────
        self.summary = QLabel("")
        self.summary.setStyleSheet(f"""
            QLabel {{
                background: {Colors.PRIMARY_BG};
                border: 1px solid rgba(0,180,216,0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: {Colors.TEXT_PRIMARY};
                font-weight: 600;
                font-size: 13px;
            }}
        """)
        root.addWidget(self.summary)

        # ── Table ─────────────────────────────────────────────────
        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(["Time", "Camera", "Zone", "Type", "Name/Plate", "Dept/Province/Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, stretch=1)

        self.status = QLabel("Ready")
        self.status.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        root.addWidget(self.status)

        # ── Connections ───────────────────────────────────────────
        self.btn_refresh.clicked.connect(self.fetch_data)
        self.btn_export.clicked.connect(self.export_csv)
        self.typing_timer = QTimer(self)
        self.typing_timer.setInterval(350)
        self.typing_timer.setSingleShot(True)
        self.typing_timer.timeout.connect(self.fetch_data)
        self.q_line.textChanged.connect(self.typing_timer.start)
        self.btn_today.clicked.connect(self._quick_today)
        self.btn_24h.clicked.connect(self._quick_24h)
        self.btn_7d.clicked.connect(self._quick_7d)
        self.fetch_data()

    def _populate_departments(self):
        self.dept_cb.clear()
        self.dept_cb.addItem("ทั้งหมด", None)
        self.dept_cb.addItem("ไม่มีแผนก", "")
        try:
            cams = self.parent().api.list_cameras()
            comps = sorted(set((c.get("comp") or "") for c in cams))
            for comp in comps:
                if comp: self.dept_cb.addItem(comp, comp)
        except Exception:
            pass

    def _quick_today(self):
        today = QDate.currentDate()
        self.start_dt.setDateTime(QDateTime(today, QTime(0, 0, 0)))
        self.end_dt.setDateTime(QDateTime.currentDateTime())
        self.fetch_data()

    def _quick_24h(self):
        end = QDateTime.currentDateTime()
        self.start_dt.setDateTime(end.addSecs(-24 * 3600))
        self.end_dt.setDateTime(end)
        self.fetch_data()

    def _quick_7d(self):
        end = QDateTime.currentDateTime()
        self.start_dt.setDateTime(end.addDays(-7))
        self.end_dt.setDateTime(end)
        self.fetch_data()

    def fetch_data(self):
        self.status.setText("Fetching data...")
        self.btn_refresh.setEnabled(False)
        try:
            start = self.start_dt.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            end = self.end_dt.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            params = {"start": start, "end": end, "limit": self.limit_spin.value()}
            dept = self.dept_cb.itemData(self.dept_cb.currentIndex())
            if dept is not None: params["department"] = dept if dept != "" else ""
            type_val = self.type_cb.currentText()
            if type_val == "Face": params["type_"] = "face"
            elif type_val == "Car": params["type_"] = "car"
            q_main = self.q_line.text().strip()
            q_cam = self.camera_code.text().strip()
            all_q = [t for t in q_main.split() if t]
            if q_cam: all_q.append(q_cam)
            if all_q: params["q"] = " ".join(all_q)
            data = self.parent().api.list_reports(**params)
            items = data.get("items", [])
            self.populate_table(items)
            face_count = sum(1 for it in items if it.get("type") == "face")
            car_count = len(items) - face_count
            self.summary.setText(f"📊 Total: {len(items)}  |  👤 Face: {face_count}  |  🚗 Car: {car_count}")
            self.status.setText(f"Done • {len(items)} rows")
        except Exception as e:
            self.status.setText(f"Error: {e}")
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self.btn_refresh.setEnabled(True)

    def populate_table(self, items):
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        for it in items:
            r = self.table.rowCount()
            self.table.insertRow(r)
            ts = it.get("timestamp", "")
            dt_obj = datetime.fromisoformat(ts.replace("Z", "+00:00")) if "T" in ts else datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            self.table.setItem(r, 0, QTableWidgetItem(dt_obj.strftime("%d %b %H:%M")))
            self.table.setItem(r, 1, QTableWidgetItem(it.get("camera_name", "")))
            self.table.setItem(r, 2, QTableWidgetItem(it.get("zone", "")))
            type_icon = "👤" if it.get("type") == "face" else "🚗"
            self.table.setItem(r, 3, QTableWidgetItem(type_icon))
            if it.get("type") == "face":
                name = it.get("full_name", "")
                emp_id = it.get("emp_id", "")
                display = f"{name}" + (f" ({emp_id})" if emp_id else "")
            else:
                display = it.get("plate", "")
            self.table.setItem(r, 4, QTableWidgetItem(display))
            if it.get("type") == "face":
                dept = it.get("department", "")
                conf = it.get("confidence")
                sim = it.get("similarity")
                extra = []
                if conf: extra.append(f"Conf:{conf:.1%}")
                if sim: extra.append(f"Sim:{sim:.1%}")
                display = dept + (f" | {' | '.join(extra)}" if extra else "")
            else:
                prov = it.get("province", "")
                status = it.get("status", "")
                display = prov + (f" | {status}" if status else "")
            self.table.setItem(r, 5, QTableWidgetItem(display))
        self.table.setSortingEnabled(True)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Report",
                                              f"report_{QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}.csv",
                                              "CSV Files (*.csv)")
        if not path: return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Time", "Camera", "Zone", "Type", "Name/Plate", "Department/Province"])
            for r in range(self.table.rowCount()):
                row = [self.table.item(r, c).text() if self.table.item(r, c) else "" for c in range(self.table.columnCount())]
                w.writerow(row)
        QMessageBox.information(self, "Success", f"CSV saved to {path}")


# ══════════════════════════════════════════════════════════════════
#   Recordings Dialog
# ══════════════════════════════════════════════════════════════════

class RecordingsDialog(QDialog):
    PAGE_SIZE = None

    def __init__(self, parent=None, camera_name: Optional[str] = None, zone: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle(f"Recordings - {camera_name or 'Unknown Camera'}")
        self.setMinimumSize(1400, 780)
        self.setStyleSheet(DIALOG_STYLESHEET)

        self.api = getattr(parent, 'api', None)
        self.camera_name = camera_name or "Unknown"
        self.zone = zone or "Unknown"

        self._all_items: list = []
        self._view_items: list = []
        self._files: list = []
        self._page: int = 1
        self._current_item: Optional[dict] = None
        self._current_video_start_dt: Optional[datetime] = None
        self._player_is_maximized = False

        self._build_ui()
        QTimer.singleShot(100, self.reload)

    def _build_ui(self):
        # ── Top Toolbar ───────────────────────────────────────────
        self.top_toolbar = QToolBar(self)
        self.top_toolbar.setMovable(False)
        self.top_toolbar.setIconSize(QSize(20, 20))

        lbl_cam = QLabel(f"📷 <b>{self.camera_name}</b>  |  Zone: <b>{self.zone}</b>")
        lbl_cam.setStyleSheet(f"""
            font-size: 13px; padding: 4px 12px;
            background: {Colors.PRIMARY_BG};
            border: 1px solid rgba(0,180,216,0.15);
            border-radius: 8px;
        """)
        self.top_toolbar.addWidget(lbl_cam)
        self.top_toolbar.addSeparator()

        self.top_toolbar.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setFixedWidth(140)
        self.date_edit.dateChanged.connect(self.reload)
        self.top_toolbar.addWidget(self.date_edit)

        btn_prev = QAction(self.style().standardIcon(QStyle.SP_ArrowLeft), "Previous Day", self)
        btn_today = QAction(self.style().standardIcon(QStyle.SP_BrowserReload), "Today", self)
        btn_next = QAction(self.style().standardIcon(QStyle.SP_ArrowRight), "Next Day", self)
        btn_prev.triggered.connect(lambda: self.date_edit.setDate(self.date_edit.date().addDays(-1)))
        btn_next.triggered.connect(lambda: self.date_edit.setDate(self.date_edit.date().addDays(1)))
        btn_today.triggered.connect(lambda: self.date_edit.setDate(QDate.currentDate()))
        self.top_toolbar.addAction(btn_prev)
        self.top_toolbar.addAction(btn_today)
        self.top_toolbar.addAction(btn_next)
        self.top_toolbar.addSeparator()

        self.top_toolbar.addWidget(QLabel("Search Person:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 ค้นหาบุคคล (Enter เพื่อค้นหา)...")
        self.search_edit.setFixedWidth(260)
        self.top_toolbar.addWidget(self.search_edit)

        self.btn_search = QPushButton("🔎 Search")
        self.btn_search.setObjectName("secondaryBtn")
        self.top_toolbar.addWidget(self.btn_search)
        self.top_toolbar.addSeparator()

        self.top_toolbar.addWidget(QLabel("Size ≥ (MB):"))
        self.min_size = QDoubleSpinBox()
        self.min_size.setRange(0, 9999)
        self.min_size.setDecimals(1)
        self.min_size.setValue(0.0)
        self.min_size.setFixedWidth(80)
        self.top_toolbar.addWidget(self.min_size)

        btn_refresh = QAction(self.style().standardIcon(QStyle.SP_BrowserReload), "Refresh", self)
        btn_refresh.triggered.connect(self.reload)
        self.top_toolbar.addSeparator()
        self.top_toolbar.addAction(btn_refresh)

        # ── Splitter ──────────────────────────────────────────────
        self.split = QSplitter(self)
        self.split.setHandleWidth(6)

        # LEFT: Table + Detections
        self.left_wrap = QWidget()
        lv = QVBoxLayout(self.left_wrap)
        lv.setContentsMargins(8, 8, 8, 8)

        self.left_splitter = QSplitter(Qt.Vertical)
        self.left_splitter.setHandleWidth(6)

        table_w = QWidget()
        tl = QVBoxLayout(table_w)
        tl.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels(["Time", "Display Name", "Filename", "Size (MB)", "🖼️ Thumb", "▶ Play", "⤓ DL"])
        h = self.table.horizontalHeader()
        modes = [QHeaderView.ResizeToContents, QHeaderView.Stretch, QHeaderView.ResizeToContents,
                 QHeaderView.ResizeToContents, QHeaderView.Fixed, QHeaderView.Fixed, QHeaderView.Fixed]
        for i, mode in enumerate(modes): h.setSectionResizeMode(i, mode)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 70)
        self.table.setColumnWidth(6, 70)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        tl.addWidget(self.table, 1)

        pag = QHBoxLayout()
        self.lbl_count = QLabel("0 item(s)")
        self.lbl_count.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        pag.addWidget(self.lbl_count)
        pag.addStretch(1)
        self.btn_prev_page = QPushButton("◀ Previous")
        self.btn_prev_page.setObjectName("secondaryBtn")
        self.lbl_page = QLabel("Page 1/1")
        self.lbl_page.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        self.btn_next_page = QPushButton("Next ▶")
        self.btn_next_page.setObjectName("secondaryBtn")
        pag.addWidget(self.btn_prev_page)
        pag.addWidget(self.lbl_page)
        pag.addWidget(self.btn_next_page)
        tl.addLayout(pag)

        self.detections_gb = QGroupBox("Detections in this Video")
        det_lay = QVBoxLayout(self.detections_gb)
        self.detection_list = QListWidget()
        self.detection_list.itemClicked.connect(self._on_detection_clicked)
        det_lay.addWidget(self.detection_list)

        self.left_splitter.addWidget(table_w)
        self.left_splitter.addWidget(self.detections_gb)
        self.left_splitter.setStretchFactor(0, 3)
        self.left_splitter.setStretchFactor(1, 1)
        self.left_splitter.setSizes([600, 200])
        lv.addWidget(self.left_splitter)

        # RIGHT: Player + Info
        right_wrap = QWidget()
        rv = QVBoxLayout(right_wrap)
        rv.setContentsMargins(8, 8, 8, 8)

        self.player = YouTubeLikePlayer(self)
        self.player.doubleClicked.connect(self.toggle_player_maximize)
        self.player.setMinimumHeight(380)
        rv.addWidget(self.player, 2)

        self.info_gb = QGroupBox("Selected File Info")
        f = QFormLayout(self.info_gb)
        self.lbl_disp = QLabel("-")
        self.lbl_file = QLabel("-")
        self.lbl_url = QLineEdit()
        self.lbl_url.setReadOnly(True)
        self.btn_copy_url = QPushButton("📋 Copy URL")
        self.btn_copy_url.setObjectName("secondaryBtn")
        self.btn_copy_url.setFixedWidth(110)
        url_row = QHBoxLayout()
        url_row.addWidget(self.lbl_url, 1)
        url_row.addWidget(self.btn_copy_url)
        self.lbl_size = QLabel("-")
        f.addRow("Display Name:", self.lbl_disp)
        f.addRow("Filename:", self.lbl_file)
        f.addRow("URL:", url_row)
        f.addRow("Size:", self.lbl_size)
        rv.addWidget(self.info_gb)

        act_row = QHBoxLayout()
        self.btn_open_external = QPushButton("🎬 Open External")
        self.btn_open_external.setObjectName("secondaryBtn")
        self.btn_download = QPushButton("⤓ Download File")
        act_row.addWidget(self.btn_open_external)
        act_row.addStretch(1)
        act_row.addWidget(self.btn_download)
        self.action_buttons_widget = QWidget()
        self.action_buttons_widget.setLayout(act_row)
        rv.addWidget(self.action_buttons_widget)

        self.split.addWidget(self.left_wrap)
        self.split.addWidget(right_wrap)
        self.split.setStretchFactor(0, 2)
        self.split.setStretchFactor(1, 3)
        self.split.setSizes([600, 800])

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.top_toolbar)
        root.addWidget(self.split, 1)

        # ── Connections ───────────────────────────────────────────
        self.search_edit.returnPressed.connect(self.reload)
        self.btn_search.clicked.connect(self.reload)
        self.min_size.valueChanged.connect(self._refilter)
        self.table.cellClicked.connect(self._cell_clicked)
        self.btn_prev_page.clicked.connect(lambda: self._goto_page(self._page - 1))
        self.btn_next_page.clicked.connect(lambda: self._goto_page(self._page + 1))
        self.btn_copy_url.clicked.connect(self._copy_url)
        self.btn_open_external.clicked.connect(self._open_external)
        self.btn_download.clicked.connect(self._download_current)

        self._debounce = QTimer(self)
        self._debounce.setInterval(350)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._refilter)

    # ── Player Maximize ───────────────────────────────────────────
    def toggle_player_maximize(self):
        self._player_is_maximized = not self._player_is_maximized
        mx = self._player_is_maximized
        self.top_toolbar.setVisible(not mx)
        self.left_wrap.setVisible(not mx)
        self.info_gb.setVisible(not mx)
        self.action_buttons_widget.setVisible(not mx)
        handle = self.split.handle(1)
        if handle: handle.setVisible(not mx)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self._player_is_maximized:
            self.toggle_player_maximize()
            e.accept()
            return
        if self.player.hasFocus() or self.player.video.hasFocus():
            self.player.keyPressEvent(e)
            e.accept()
            return
        super().keyPressEvent(e)

    # ── Data Loading ──────────────────────────────────────────────
    def _selected_date_str(self) -> str:
        return self.date_edit.date().toString("yyyy-MM-dd")

    def _build_stream_url(self, it: dict) -> str:
        department = it.get("department", "")
        date_str = it.get("date", self._selected_date_str())
        filename = it.get("file") or it.get("filename", "")
        base = CONFIG.get("SERVER_BASE", "").rstrip("/")
        if not base: return ""
        path_parts = ["recordings", department, self.zone, self.camera_name, date_str, filename]
        clean_path = "/".join(part for part in path_parts if part)
        base_url = f"{base}/{clean_path}"
        try:
            token = getattr(self.api, 'token', None)
            if not token: return base_url
            u = urlparse(base_url)
            qs = dict(parse_qsl(u.query))
            qs["token"] = token
            return urlunparse((u.scheme, u.netloc, u.path, u.params, urlencode(qs), u.fragment))
        except Exception:
            return base_url

    def reload(self):
        if not self.api:
            QMessageBox.critical(self, "Error", "API Client not available.")
            return
        self._clear_state()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            target = self._selected_date_str()
            person = self.search_edit.text().strip()
            self._all_items = self.api.list_recordings(self.camera_name, self.zone, date=target, person_name=person) or []
            self._all_items.sort(key=lambda x: x.get("modified", ""), reverse=True)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to load recordings:\n{str(e)}")
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._refilter()

    def _clear_state(self):
        self._all_items = []
        self._view_items = []
        self._files = []
        self._page = 1
        self._current_item = None
        self.table.setRowCount(0)
        if hasattr(self.player, 'stop'): self.player.stop()
        self._clear_info_panel()
        if hasattr(self, 'detection_list'): self.detection_list.clear()

    def _clear_info_panel(self):
        self.lbl_disp.setText("-")
        self.lbl_file.setText("-")
        self.lbl_url.setText("")
        self.lbl_size.setText("-")
        self.btn_copy_url.setEnabled(False)
        self.btn_open_external.setEnabled(False)
        self.btn_download.setEnabled(False)
        if hasattr(self, 'detection_list'): self.detection_list.clear()

    def _refilter(self):
        min_mb = float(self.min_size.value())
        self._view_items = [it for it in self._all_items if float(it.get("size_mb", 0.0)) >= min_mb]
        self._page = 1
        self._refresh_page()

    def _refresh_page(self):
        total = len(self._view_items)
        was_sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)

        if self.PAGE_SIZE is None:
            pages = 1; self._page = 1
            self._files = self._view_items
        else:
            pages = max(1, (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
            self._page = max(1, min(self._page, pages))
            start = (self._page - 1) * self.PAGE_SIZE
            end = min(start + self.PAGE_SIZE, total)
            self._files = self._view_items[start:end]

        self.table.setRowCount(len(self._files))
        for idx, it in enumerate(self._files):
            r = idx
            modified_iso = it.get("modified", "")
            time_display = it.get("date", "-")
            if modified_iso and "T" in str(modified_iso):
                try:
                    dt_obj = datetime.fromisoformat(modified_iso.replace("Z", "+00:00"))
                    time_display = dt_obj.strftime("%H:%M:%S") + f" ({it.get('date', '')})"
                except ValueError:
                    try: time_display = f"{str(modified_iso).split('T')[1][:8]} ({it.get('date', '-')})"
                    except: pass
            time_item = QTableWidgetItem(time_display)
            time_item.setData(Qt.UserRole, modified_iso)
            self.table.setItem(r, 0, time_item)
            self.table.setItem(r, 1, QTableWidgetItem(it.get("display_name") or "-"))
            self.table.setItem(r, 2, QTableWidgetItem(it.get("file") or it.get("filename", "-")))
            size_mb = it.get('size_mb', 0.0)
            size_item = QTableWidgetItem(f"{size_mb:.1f}")
            size_item.setData(Qt.UserRole, it.get('size_bytes', 0))
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(r, 3, size_item)

            thumb = QLabel("🎬")
            thumb.setAlignment(Qt.AlignCenter)
            thumb.setStyleSheet(f"background: {Colors.BG_ELEVATED}; border: 1px solid {Colors.BORDER}; border-radius: 6px;")
            thumb.setFixedSize(88, 50)
            self.table.setCellWidget(r, 4, thumb)

            btn_play = QPushButton("▶")
            btn_play.setProperty("row", r)
            btn_play.clicked.connect(self._play_row)
            btn_play.setFixedSize(65, 32)
            self.table.setCellWidget(r, 5, btn_play)

            btn_dl = QPushButton("⤓")
            btn_dl.setProperty("row", r)
            btn_dl.setObjectName("secondaryBtn")
            btn_dl.clicked.connect(self._download_row)
            btn_dl.setFixedSize(65, 32)
            self.table.setCellWidget(r, 6, btn_dl)

        self.table.setSortingEnabled(was_sorting)
        self.lbl_count.setText(f"{total} item(s)")
        self.lbl_page.setText(f"Page {self._page}/{pages}")
        self.btn_prev_page.setEnabled(self._page > 1)
        self.btn_next_page.setEnabled(self._page < pages)

    def _goto_page(self, p: int):
        if self.PAGE_SIZE is None: return
        total_pages = max(1, (len(self._view_items) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self._page = max(1, min(p, total_pages))
        self._refresh_page()

    def _row_item(self, row: int) -> Optional[dict]:
        return self._files[row] if 0 <= row < len(self._files) else None

    def _cell_clicked(self, row: int, col: int):
        if col not in (5, 6): self._preview_row(row)

    def _preview_row(self, row: int):
        it = self._row_item(row)
        if not it:
            self._clear_info_panel()
            if hasattr(self.player, 'stop'): self.player.stop()
            self.detection_list.clear()
            self._current_video_start_dt = None
            return
        self._current_item = it
        url = self._build_stream_url(it)
        self.lbl_disp.setText(it.get("display_name") or "-")
        self.lbl_file.setText(it.get("file") or it.get("filename", "-"))
        self.lbl_url.setText(url)
        self.lbl_size.setText(f"{it.get('size_mb', 0):.1f} MB")
        self.btn_copy_url.setEnabled(bool(url))
        self.btn_open_external.setEnabled(bool(url))
        self.btn_download.setEnabled(True)
        try:
            self._current_video_start_dt = _parse_video_start_time(it.get("date"), it.get("file"))
        except Exception:
            self._current_video_start_dt = None
        try:
            self.player.set_media(url)
            self._fetch_detections_for_item(it)
        except Exception as e:
            QMessageBox.warning(self, "Player Error", f"Cannot load preview:\n{str(e)}")

    def _fetch_detections_for_item(self, it: dict):
        if not hasattr(self, 'detection_list'): return
        self.detection_list.clear()
        self.detection_list.addItem("🔄 Loading detections...")
        filename = it.get("file") or it.get("filename")
        camera = it.get("camera", self.camera_name)
        zone = it.get("zone", self.zone)
        date = it.get("date", self._selected_date_str())
        if not filename or not self.api:
            self.detection_list.clear()
            self.detection_list.addItem("❌ Error: Missing file info or API.")
            return
        def _task():
            try:
                dets = self.api.get_detections_for_file(filename, camera, zone, date)
                self.detection_list.clear()
                if not dets:
                    self.detection_list.addItem("ℹ️ No detections found in this video.")
                    return
                for det in dets:
                    icon = "👤" if det.get("type") == "face" else "🚗"
                    name = det.get("full_name") or det.get("plate") or "Unknown"
                    ts = det.get("timestamp", "")
                    time_str = ""
                    try:
                        if "T" in ts: time_str = ts.split("T")[-1].split(".")[0]
                        elif " " in ts: time_str = ts.split(" ")[-1]
                    except: pass
                    item = QListWidgetItem(f"{icon} [{time_str}] {name}")
                    item.setData(Qt.UserRole, det.get("timestamp"))
                    self.detection_list.addItem(item)
            except Exception as e:
                self.detection_list.clear()
                self.detection_list.addItem(f"❌ Error: {str(e)}")
        QTimer.singleShot(0, _task)

    def _play_row(self):
        btn = self.sender()
        if not btn: return
        row = btn.property("row")
        if row is not None and row >= 0:
            self._preview_row(row)
            if hasattr(self.player, 'play'):
                QTimer.singleShot(50, self.player.play)

    def _download_row(self):
        btn = self.sender()
        if not btn: return
        row = btn.property("row")
        if row is not None and row >= 0:
            self._download_item(self._row_item(row))

    def _copy_url(self):
        url = self.lbl_url.text().strip()
        if url:
            QApplication.clipboard().setText(url)
            QMessageBox.information(self, "Copied", "URL copied to clipboard! 📋")

    def _open_external(self):
        url_str = self.lbl_url.text().strip()
        if url_str:
            if not QDesktopServices.openUrl(QUrl(url_str)):
                QMessageBox.warning(self, "Error", f"Could not open URL:\n{url_str}")

    def _download_current(self):
        if not self._current_item:
            QMessageBox.information(self, "Download", "Please select a file first.")
            return
        self._download_item(self._current_item)

    def _download_item(self, it: Optional[dict]):
        if not it or not self.api:
            QMessageBox.warning(self, "Download Error", "Missing item data or API.")
            return
        filename = it.get("file") or it.get("filename", "recording.mp4")
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Video File",
                                                   os.path.join(default_dir, filename),
                                                   "MP4 Files (*.mp4);;All Files (*)")
        if not save_path: return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            dept = it.get("department", "")
            zone = it.get("zone", self.zone)
            cam = it.get("camera", self.camera_name)
            file = it.get("file") or it.get("filename", "")
            date = it.get("date", self._selected_date_str())
            if not all([dept, zone, cam, file, date]):
                raise ValueError("Missing required download info.")
            self.api.download_recording(dept, zone, cam, file, save_path, date=date)
            QMessageBox.information(self, "Download Complete", f"✅ Video saved to:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Download Error", f"Failed:\n{str(e)}")
        finally:
            QApplication.restoreOverrideCursor()

    @pyqtSlot(QListWidgetItem)
    def _on_detection_clicked(self, item: QListWidgetItem):
        ts_str = item.data(Qt.UserRole)
        if not ts_str or not self._current_video_start_dt: return
        try:
            det_dt = datetime.fromisoformat(ts_str)
            offset_ms = int((det_dt - self._current_video_start_dt).total_seconds() * 1000)
            if offset_ms < 0: offset_ms = 0
            if hasattr(self.player, 'player') and self.player.player.isSeekable():
                self.player.player.setPosition(offset_ms)
                if self.player.player.state() != QMediaPlayer.PlayingState:
                    self.player.play()
        except Exception as e:
            logger.error(f"Error seeking to detection: {e}")

    def closeEvent(self, event):
        if hasattr(self.player, 'stop'): self.player.stop()
        super().closeEvent(event)
