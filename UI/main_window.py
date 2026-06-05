"""
main_window.py — Main application window with toolbar, camera grid, and sidebar.
"""
from config import *
from theme import *
from utils import *
from api_client import *
from components import *
from auth_dialogs import *
from employee_dialogs import *
from camera_dialogs import *
from admin_dialogs import *


class DeepBlueGridUltimate(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api = APIClient(CONFIG["SERVER_BASE"])
        self.setWindowTitle("AI-CCTV Client — Ultimate Grid Edition")
        self.setMinimumSize(1300, 800)
        self.open_dialogs: Dict[str, QDialog] = {}

        if os.path.exists(LOGO_PATH):
            icon = QIcon(LOGO_PATH)
            self.setWindowIcon(icon)
            QApplication.setWindowIcon(icon)

        self.maximized_tile: Optional[CameraStreamTile] = None
        self.green_icon = self._create_status_icon(QColor(Colors.SUCCESS))
        self.red_icon   = self._create_status_icon(QColor(Colors.DANGER))
        self.gray_icon  = self._create_status_icon(QColor(Colors.TEXT_DISABLED))

        self.ui_ws_client: Optional[UIWebSocketClient] = None
        self.btn_segment = None
        self.act_admin = None
        self.btn_admin = None

        self._apply_styles()
        self._build_ui()

        self.employee_count_label = QLabel("👥 Employees: (Loading...)")
        self.employee_count_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 0 10px; font-size: 12px;")
        self.statusBar().addPermanentWidget(self.employee_count_label)

    def _apply_styles(self):
        self.setStyleSheet(GLOBAL_STYLESHEET)

    def _build_ui(self):
        # ── Toolbar ───────────────────────────────────────────────
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(22, 22))
        self.addToolBar(Qt.TopToolBarArea, tb)
        self.toolBar = tb

        style = self.style()
        self.act_refresh    = QAction(style.standardIcon(QStyle.SP_BrowserReload), "Refresh Cameras", self)
        self.act_reports    = QAction(style.standardIcon(QStyle.SP_FileDialogDetailedView), "Reports", self)
        self.act_recordings = QAction(style.standardIcon(QStyle.SP_DriveDVDIcon), "Recordings", self)
        self.act_logout     = QAction(style.standardIcon(QStyle.SP_DialogCloseButton), "Logout", self)

        def add_btn(action):
            btn = QToolButton()
            btn.setDefaultAction(action)
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            tb.addWidget(btn)
            return btn

        add_btn(self.act_refresh)
        tb.addSeparator()
        add_btn(self.act_reports)
        add_btn(self.act_recordings)
        add_btn(self.act_logout)

        # ── Central Splitter ──────────────────────────────────────
        splitter = QSplitter()
        splitter.setHandleWidth(5)
        self.setCentralWidget(splitter)

        # ── Left Sidebar ──────────────────────────────────────────
        left = QWidget()
        left.setStyleSheet(f"background: {Colors.BG_DARK};")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(12, 12, 12, 12)
        lv.setSpacing(10)

        self.lbl_user = QLabel("Welcome, Guest")
        self.lbl_user.setStyleSheet(f"""
            font-size: 16px; font-weight: 600;
            color: {Colors.TEXT_PRIMARY};
            padding: 8px 0;
        """)
        lv.addWidget(self.lbl_user)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Search Cameras...")
        self.search.setFixedHeight(38)
        lv.addWidget(self.search)

        self.comp_filter_cb = QComboBox()
        lv.addWidget(self.comp_filter_cb)

        self.cam_list = QListWidget()
        self.cam_list.setSelectionMode(QAbstractItemView.NoSelection)
        lv.addWidget(self.cam_list, 1)

        hl = QHBoxLayout()
        self.btn_select_all = QPushButton("Select All (≤9)")
        self.btn_select_all.setObjectName("secondaryBtn")
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setObjectName("clearButton")
        hl.addWidget(self.btn_select_all)
        hl.addWidget(self.btn_clear)
        lv.addLayout(hl)

        self.btn_apply = QPushButton("▶ Apply Selection")
        self.btn_apply.setFixedHeight(40)
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        lv.addWidget(self.btn_apply)

        # ── Right Grid ────────────────────────────────────────────
        right = QWidget()
        right.setStyleSheet(f"background: {Colors.BG_DARKEST};")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(8, 8, 8, 8)
        self.grid_wrap = QWidget()
        self.grid = QGridLayout(self.grid_wrap)
        self.grid.setSpacing(10)
        self.grid.setContentsMargins(6, 6, 6, 6)
        rv.addWidget(self.grid_wrap, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 980])

        self.statusBar().showMessage("Ready")

        # ── Connections ───────────────────────────────────────────
        self.act_refresh.triggered.connect(self.load_cameras)
        self.btn_select_all.clicked.connect(self.select_all_9)
        self.btn_clear.clicked.connect(self.clear_checks)
        self.btn_apply.clicked.connect(self.apply_selection)
        self.search.textChanged.connect(self._filter_list)
        self.comp_filter_cb.currentIndexChanged.connect(self._filter_list)
        self.act_logout.triggered.connect(self.logout)
        self.act_reports.triggered.connect(self.show_reports)
        self.act_recordings.triggered.connect(self.show_recordings)

        QTimer.singleShot(50, self._ensure_login)

    # ── Toolbar Rebuild ───────────────────────────────────────────
    def _rebuild_toolbar(self):
        tb = self.toolBar
        if not tb: return
        for action in list(tb.actions()):
            if action != self.act_logout:
                tb.removeAction(action)
        layout = tb.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget and widget.defaultAction() != self.act_logout:
                    widget.setParent(None)
                    widget.deleteLater()

        style = self.style()
        def add_btn(action):
            btn = QToolButton()
            btn.setDefaultAction(action)
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            tb.addWidget(btn)
            return btn

        add_btn(self.act_refresh)
        tb.addSeparator()
        add_btn(self.act_reports)
        add_btn(self.act_recordings)

        is_admin = bool(getattr(self.api, "is_admin", False))
        if is_admin:
            if not self.btn_segment:
                self.btn_segment = QToolButton()
                self.btn_segment.setText("Segment: 1 min")
                self.btn_segment.setIcon(style.standardIcon(QStyle.SP_FileDialogContentsView))
                self.btn_segment.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
                self.btn_segment.setPopupMode(QToolButton.InstantPopup)
                self.btn_segment.setMenu(self._create_segment_menu())
            tb.addWidget(self.btn_segment)
            tb.addSeparator()
            if not self.act_admin:
                self.act_admin = QAction(style.standardIcon(QStyle.SP_ComputerIcon), "Admin", self)
                self.act_admin.triggered.connect(self.show_admin)
            if not self.btn_admin:
                self.btn_admin = add_btn(self.act_admin)
            else:
                tb.addWidget(self.btn_admin)
            tb.addSeparator()
        else:
            if self.btn_segment: self.btn_segment.setParent(None); self.btn_segment = None
            if self.btn_admin: self.btn_admin.setParent(None); self.btn_admin = None
            if self.act_admin: self.act_admin = None

        add_btn(self.act_logout)
        logger.info(f"Toolbar rebuilt. Admin: {'Yes' if is_admin else 'No'}")

    # ── Auth ──────────────────────────────────────────────────────
    def _ensure_login(self):
        dlg = DeepBlueLoginDialog(self.api, self)
        if dlg.exec_() == QDialog.Accepted:
            self.lbl_user.setText(f"Welcome, {self.api.username or 'User'}")
            self._rebuild_toolbar()
            self.load_cameras()
            self._start_ui_websocket()
        else:
            QApplication.quit()

    def logout(self):
        self._clear_grid_tiles()
        self.cam_list.clear()
        try: self.api.logout()
        except: pass
        self.lbl_user.setText("Welcome, Guest")
        if hasattr(self, "employee_count_label"):
            self.employee_count_label.setText("👥 Employees: 0")
        if hasattr(self, "ui_ws_client") and self.ui_ws_client:
            self.ui_ws_client.stop()
        self._rebuild_toolbar()
        for d in list(self.open_dialogs.values()): d.close()
        self.open_dialogs.clear()
        QMessageBox.information(self, "Logout", "ออกจากระบบเรียบร้อย")
        self._ensure_login()

    def show_admin(self):
        if not bool(getattr(self.api, "is_admin", False)):
            QMessageBox.warning(self, "Access Denied", "คุณไม่มีสิทธิ์เข้าใช้งาน Admin Tools")
            return
        try:
            hub = AdminHub(self.api, self)
            hub.exec_()
            self.load_cameras()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ── Status Icons ──────────────────────────────────────────────
    def _create_status_icon(self, color: QColor) -> QIcon:
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(3, 3, 10, 10)
        painter.end()
        return QIcon(pixmap)

    @pyqtSlot(dict)
    def on_health_status_update(self, status_dict: dict):
        self.statusBar().setToolTip(f"Last status update: {datetime.now().strftime('%H:%M:%S')}")
        for i in range(self.cam_list.count()):
            item = self.cam_list.item(i)
            if not item: continue
            cam_data = item.data(Qt.UserRole)
            if not isinstance(cam_data, dict): continue
            cam_name = cam_data.get("camera_name")
            if not cam_name: continue
            status = status_dict.get(cam_name, "UNKNOWN")
            if status == "OK":
                item.setIcon(self.green_icon)
                item.setToolTip("Status: OK (Running)")
            elif status == "DOWN":
                item.setIcon(self.red_icon)
                item.setToolTip("Status: DOWN (Connection Lost)")
            else:
                item.setIcon(self.gray_icon)
                item.setToolTip("Status: Unknown")

    # ── WebSocket ─────────────────────────────────────────────────
    def _start_ui_websocket(self):
        if self.ui_ws_client: self.ui_ws_client.stop()
        self.ui_ws_client = UIWebSocketClient(self.api)
        self.ui_ws_client.status_updated.connect(self.on_health_status_update)
        self.ui_ws_client.connection_lost.connect(
            lambda msg: self.statusBar().showMessage(
                "Real-time status: Connected" if not msg else f"Real-time status: Disconnected ({msg})"
            ))
        self.ui_ws_client.start()

    # ── Segment Menu ──────────────────────────────────────────────
    def _create_segment_menu(self) -> QMenu:
        menu = QMenu(self)
        for minutes in [1, 2, 3]:
            action = QAction(f"{minutes} minutes", self)
            action.triggered.connect(lambda _, m=minutes: self._set_segment_time(m))
            menu.addAction(action)
        return menu

    def _set_segment_time(self, minutes: int):
        self.statusBar().showMessage(f"Setting segment time to {minutes} minutes...")
        QApplication.processEvents()
        try:
            result = self.api.set_segment_minutes(minutes)
            new_mins = result.get("new_segment_minutes", minutes)
            if self.btn_segment: self.btn_segment.setText(f"Segment: {new_mins} min")
            self.statusBar().showMessage(f"Segment time set to {new_mins} minutes.")
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to set segment time:\n{str(e)}")

    # ── Camera Loading ────────────────────────────────────────────
    def load_cameras(self):
        self.cam_list.clear()
        self.comp_filter_cb.clear()
        try:
            cams = self.api.list_cameras()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load cameras: {e}")
            return
        all_comps = sorted(list(set(c.get("comp") for c in cams if c.get("comp"))))
        self.comp_filter_cb.addItem("All Departments", None)
        for comp in all_comps: self.comp_filter_cb.addItem(comp, comp)
        for cam in cams:
            name = cam.get("camera_name") or cam.get("camera_code", "")
            item = QListWidgetItem(name)
            item.setIcon(self.gray_icon)
            item.setToolTip("Status: Unknown")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.cam_list.addItem(item)
            item.setData(Qt.UserRole, cam)
        try:
            employees = self.api.list_employees()
            self.employee_count_label.setText(f"👥 Employees: {len(employees)}")
        except Exception as e:
            logger.error(f"Failed to load employee count: {e}")
            self.employee_count_label.setText("👥 Employees: Error")
        self.statusBar().showMessage(f"Loaded {self.cam_list.count()} cameras.")

    def current_checked_names(self) -> List[str]:
        names = []
        for i in range(self.cam_list.count()):
            if self.cam_list.item(i).checkState() == Qt.Checked:
                cam_data = self.cam_list.item(i).data(Qt.UserRole)
                if isinstance(cam_data, dict):
                    name = cam_data.get("camera_name")
                    if name: names.append(name)
                elif isinstance(cam_data, str):
                    names.append(cam_data)
        return names

    def select_all_9(self):
        for i in range(self.cam_list.count()):
            self.cam_list.item(i).setCheckState(Qt.Unchecked)
        for i in range(min(self.cam_list.count(), CONFIG["MAX_TILES"])):
            self.cam_list.item(i).setCheckState(Qt.Checked)

    def clear_checks(self):
        for i in range(self.cam_list.count()):
            self.cam_list.item(i).setCheckState(Qt.Unchecked)

    def _filter_list(self):
        search_text = self.search.text().strip().lower()
        selected_comp = self.comp_filter_cb.itemData(self.comp_filter_cb.currentIndex())
        for i in range(self.cam_list.count()):
            it = self.cam_list.item(i)
            cam_data = it.data(Qt.UserRole)
            if not isinstance(cam_data, dict):
                it.setHidden(True); continue
            cam_name = (cam_data.get("camera_name") or "").lower()
            name_match = (not search_text) or (search_text in cam_name)
            cam_comp = cam_data.get("comp")
            comp_match = (selected_comp is None) or (cam_comp == selected_comp)
            it.setHidden(not (name_match and comp_match))

    # ── Grid ──────────────────────────────────────────────────────
    def apply_selection(self):
        if self.maximized_tile: self.handle_tile_double_click()
        names = self.current_checked_names()
        if not names:
            QMessageBox.information(self, "Selection", "กรุณาเลือกกล้องอย่างน้อย 1 ตัว")
            return
        if len(names) > CONFIG["MAX_TILES"]:
            QMessageBox.warning(self, "Limit", f"เลือกได้สูงสุด {CONFIG['MAX_TILES']} ตัว")
            names = names[:CONFIG["MAX_TILES"]]
        self._clear_grid_tiles()
        row, col = 0, 0
        for name in names:
            tile = CameraStreamTile(self.api, name, self.grid_wrap)
            tile.doubleClicked.connect(self.handle_tile_double_click)
            self.grid.addWidget(tile, row, col)
            col += 1
            if col >= 3: col, row = 0, row + 1
            if row >= 3: break
        self.statusBar().showMessage(f"Showing {self.grid.count()} stream(s).")

    def _clear_grid_tiles(self):
        self.maximized_tile = None
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if isinstance(w, CameraStreamTile): w.stop_play()
            if w: w.setParent(None); w.deleteLater()

    def handle_tile_double_click(self):
        clicked = self.sender()
        if not isinstance(clicked, QWidget): return
        if self.maximized_tile:
            for i in range(self.grid.count()):
                w = self.grid.itemAt(i).widget()
                if w: w.show()
            self.maximized_tile = None
        else:
            self.maximized_tile = clicked
            for i in range(self.grid.count()):
                w = self.grid.itemAt(i).widget()
                if w and w != self.maximized_tile: w.hide()

    # ── Dialogs ───────────────────────────────────────────────────
    @pyqtSlot(int)
    def _on_dialog_finished(self):
        sender_dialog = self.sender()
        if not isinstance(sender_dialog, QDialog): return
        key_to_remove = None
        for key, inst in self.open_dialogs.items():
            if inst is sender_dialog: key_to_remove = key; break
        if key_to_remove and key_to_remove in self.open_dialogs:
            del self.open_dialogs[key_to_remove]

    def show_reports(self):
        try: ReportsDialog(self).exec_()
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def show_recordings(self):
        try:
            cams = self.api.list_cameras()
            pick = SelectCameraDialog(cams, self)
            if pick.exec_():
                cam = pick.get_selected_camera()
                if cam:
                    dlg = RecordingsDialog(self, camera_name=cam.get("camera_name"), zone=cam.get("zone", "building"))
                    dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ── Cleanup ───────────────────────────────────────────────────
    def closeEvent(self, e: QCloseEvent):
        if hasattr(self, "ui_ws_client") and self.ui_ws_client:
            self.ui_ws_client.stop()
        try:
            for d in list(self.open_dialogs.values()): d.close()
            self._clear_grid_tiles()
            if hasattr(self.api, 'logout'): self.api.logout()
        except Exception as ex:
            logger.error(f"Error during closeEvent cleanup: {ex}")
        super().closeEvent(e)
