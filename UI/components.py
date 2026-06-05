"""
components.py — Reusable UI components: YouTubeLikePlayer, CameraStreamTile, SplashScreen.
"""
from config import *
from theme import *
from api_client import APIClient, MJPGWebSocketPlayer


# ══════════════════════════════════════════════════════════════════
#   YouTube-Like Video Player
# ══════════════════════════════════════════════════════════════════

class YouTubeLikePlayer(QWidget):
    doubleClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(False)

        self.player = QMediaPlayer(self)
        self.video = QVideoWidget(self)
        self.player.setVideoOutput(self.video)
        self.video.installEventFilter(self)

        # ── Thumbnail overlay ─────────────────────────────────────
        self.thumbnail_label = QLabel(self.video)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(6,13,24,0.96), stop:1 rgba(15,31,54,0.96));
                border-radius: 10px;
                color: {Colors.TEXT_SECONDARY};
                font-size: 14px;
                padding: 20px;
            }}""")
        self.thumbnail_label.setText("🎥 เลือกวิดีโอเพื่อดูตัวอย่าง")
        self.thumbnail_label.hide()

        # ── Control bar ───────────────────────────────────────────
        self.bar = QWidget(self)
        self.bar.setStyleSheet(PLAYER_BAR_STYLE)
        bar_layout = QHBoxLayout(self.bar)
        bar_layout.setContentsMargins(14, 8, 14, 8)
        bar_layout.setSpacing(10)

        self.btn_play = QToolButton(self.bar)
        self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_play.setStyleSheet(PLAYER_BUTTON_STYLE)

        self.lbl_time = QLabel("0:00 / 0:00", self.bar)
        self.lbl_time.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-family: 'Segoe UI'; font-size: 12px; min-width: 100px;")

        self.slider = QSlider(Qt.Horizontal, self.bar)
        self.slider.setRange(0, 1000)
        self.slider.sliderMoved.connect(self.seek_slider_moved)
        self.slider.sliderPressed.connect(self._slider_pressed)
        self.slider.sliderReleased.connect(self._slider_released)
        self.slider.setStyleSheet(PLAYER_SLIDER_STYLE)

        self.btn_vol = QToolButton(self.bar)
        self.btn_vol.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
        self.btn_vol.clicked.connect(self._toggle_mute)
        self.btn_vol.setStyleSheet(PLAYER_BUTTON_STYLE)
        self._is_muted = False
        self._last_volume = 80

        self.vol_slider = QSlider(Qt.Horizontal, self.bar)
        self.vol_slider.setFixedWidth(90)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(self._last_volume)
        self.vol_slider.valueChanged.connect(self.set_volume)
        self.vol_slider.setStyleSheet(PLAYER_SLIDER_STYLE)

        self.btn_speed = QToolButton(self.bar)
        self.btn_speed.setText("1.0x")
        speed_menu = QMenu(self.btn_speed)
        speed_menu.setStyleSheet(f"""
            QMenu {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY}; border: 1px solid {Colors.BORDER}; border-radius: 8px; padding: 4px; }}
            QMenu::item {{ padding: 6px 16px; border-radius: 4px; }}
            QMenu::item:selected {{ background: {Colors.PRIMARY_BG}; color: {Colors.PRIMARY_HOVER}; }}
        """)
        for sp in [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
            act = QAction(f"{sp}x", speed_menu, triggered=lambda _, s=sp: self.set_rate(s))
            speed_menu.addAction(act)
        self.btn_speed.setMenu(speed_menu)
        self.btn_speed.setPopupMode(QToolButton.InstantPopup)
        self.btn_speed.setStyleSheet(f"""
            QToolButton {{ padding: 6px 10px; border-radius: 8px; background: rgba(255,255,255,0.06); color: {Colors.TEXT_PRIMARY}; border: 1px solid rgba(255,255,255,0.08); }}
            QToolButton:hover {{ background: rgba(0,180,216,0.15); border: 1px solid rgba(0,180,216,0.3); }}
        """)

        self.btn_fs = QToolButton(self.bar)
        self.btn_fs.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self.btn_fs.clicked.connect(self.toggle_fullscreen)
        self.btn_fs.setStyleSheet(PLAYER_BUTTON_STYLE)

        bar_layout.addWidget(self.btn_play)
        bar_layout.addWidget(self.slider, 1)
        bar_layout.addWidget(self.lbl_time)
        bar_layout.addSpacing(8)
        bar_layout.addWidget(self.btn_vol)
        bar_layout.addWidget(self.vol_slider)
        bar_layout.addSpacing(8)
        bar_layout.addWidget(self.btn_speed)
        bar_layout.addSpacing(4)
        bar_layout.addWidget(self.btn_fs)

        # ── Big play button ───────────────────────────────────────
        self.big_play = QToolButton(self.video)
        self.big_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.big_play.setIconSize(QSize(96, 96))
        self.big_play.setStyleSheet(BIG_PLAY_BUTTON_STYLE)
        self.big_play.clicked.connect(self.toggle_play)
        self.big_play.hide()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.video)

        self.bar_timer = QTimer(self)
        self.bar_timer.setInterval(2500)
        self.bar_timer.timeout.connect(self._maybe_hide_controls)

        self._mouse_active = True
        self._controls_visible = True
        self._slider_is_dragging = False

        self.player.positionChanged.connect(self._on_pos)
        self.player.durationChanged.connect(self._on_dur)
        self.player.stateChanged.connect(self._on_state)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        self.player.error.connect(self._on_player_error)
        self.player.setVolume(self._last_volume)

        self._has_thumbnail = False
        self._current_media_url = None
        self._last_position = 0

    def eventFilter(self, source, event):
        if source is self.video and event.type() == QEvent.MouseButtonDblClick:
            self.doubleClicked.emit()
            return True
        return super().eventFilter(source, event)

    def set_media(self, url_or_path: str):
        if not url_or_path: return
        logger.info(f"QMediaPlayer: Setting media to {url_or_path}")
        self._current_media_url = url_or_path
        url = QUrl.fromLocalFile(url_or_path) if os.path.exists(url_or_path) else QUrl(url_or_path)
        self.player.stop()
        self._reset_ui()
        self.player.setMedia(QMediaContent(url))
        self.show_thumbnail(True)
        self.show_controls(True)

    def set_thumbnail(self, thumbnail_path: str = None, thumbnail_bytes: bytes = None):
        pixmap = None
        if thumbnail_path and os.path.exists(thumbnail_path):
            pixmap = QPixmap(thumbnail_path)
        elif thumbnail_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(thumbnail_bytes)
        if pixmap and not pixmap.isNull():
            self.thumbnail_label.setPixmap(pixmap.scaled(self.video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self._has_thumbnail = True
        else:
            self.thumbnail_label.setText("🎥 ไม่พบตัวอย่าง")
            self.thumbnail_label.setPixmap(QPixmap())
            self._has_thumbnail = False
        self.show_thumbnail(True)

    def show_thumbnail(self, show: bool = True):
        if show:
            self.thumbnail_label.setVisible(True)
            self.thumbnail_label.raise_()
            self.big_play.setVisible(True)
            self.big_play.raise_()
            if not self._has_thumbnail:
                self.thumbnail_label.setText("🎥 เลือกวิดีโอเพื่อดูตัวอย่าง")
        else:
            self.thumbnail_label.hide()
            self.big_play.hide()

    def play(self):
        if self.player.state() != QMediaPlayer.PlayingState:
            self.player.play()

    def pause(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()

    def stop(self):
        self.player.stop()

    def toggle_play(self):
        state = self.player.state()
        if state == QMediaPlayer.PlayingState:
            self.pause()
        elif state == QMediaPlayer.PausedState:
            self.play()
        elif state == QMediaPlayer.StoppedState:
            if self.player.duration() > 0 and self._last_position >= (self.player.duration() - 1000):
                self.player.setPosition(0)
            self.play()
        elif self._current_media_url:
            self.set_media(self._current_media_url)
            self.player.play()

    def set_rate(self, r: float):
        self.player.setPlaybackRate(r)
        self.btn_speed.setText(f"{r:.2f}x")

    def _slider_pressed(self):
        self._slider_is_dragging = True

    def _slider_released(self):
        self._slider_is_dragging = False
        self.seek_slider_value(self.slider.value())

    def seek_slider_moved(self, v_int: int):
        if self.player.duration() > 0:
            pos_ms = int((v_int / 1000.0) * self.player.duration())
            self.lbl_time.setText(f"{self._fmt(pos_ms)} / {self._fmt(self.player.duration())}")

    def seek_slider_value(self, v_int: int):
        if self.player.duration() > 0 and self.player.isSeekable():
            pos_ms = int((v_int / 1000.0) * self.player.duration())
            self.player.setPosition(pos_ms)

    def set_volume(self, v_int: int):
        self.player.setVolume(v_int)
        if v_int > 0 and self._is_muted:
            self.player.setMuted(False); self._is_muted = False
        elif v_int == 0:
            self.player.setMuted(True); self._is_muted = True
        if not self._is_muted:
            self._last_volume = v_int
        self._update_volume_icon()

    def _toggle_mute(self):
        self._is_muted = not self._is_muted
        self.player.setMuted(self._is_muted)
        if not self._is_muted and self.player.volume() == 0:
            self.vol_slider.setValue(self._last_volume if self._last_volume > 0 else 80)
        self._update_volume_icon()

    def _update_volume_icon(self):
        if self._is_muted or self.player.volume() == 0:
            try:
                icon = self.style().standardIcon(QStyle.SP_MediaVolumeMuted)
                if icon.isNull(): raise AttributeError
            except AttributeError:
                icon = self.style().standardIcon(QStyle.SP_MediaVolume)
            self.btn_vol.setIcon(icon)
        else:
            self.btn_vol.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))

    def _on_pos(self, pos_ms):
        dur = self.player.duration()
        if not self._slider_is_dragging and dur > 0:
            self.slider.blockSignals(True)
            self.slider.setValue(int((pos_ms / dur) * 1000))
            self.slider.blockSignals(False)
        self.lbl_time.setText(f"{self._fmt(pos_ms)} / {self._fmt(dur)}")
        self._last_position = pos_ms

    def _on_dur(self, dur_ms):
        self.slider.setEnabled(dur_ms > 0 and self.player.isSeekable())
        self._on_pos(self.player.position())

    def _on_state(self, state):
        if state == QMediaPlayer.PlayingState:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.show_thumbnail(False)
            self.start_auto_hide()
        elif state == QMediaPlayer.PausedState:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.bar_timer.stop()
            self.show_controls(True)
        elif state == QMediaPlayer.StoppedState:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self._reset_ui()
            self.show_thumbnail(True)
            self.show_controls(True)

    def _on_media_status(self, status):
        self._reposition_overlays()
        if status == QMediaPlayer.LoadedMedia:
            self._on_dur(self.player.duration())
        elif status == QMediaPlayer.InvalidMedia:
            self._on_player_error(self.player.error())
        elif status == QMediaPlayer.EndOfMedia:
            self.player.stop()

    @pyqtSlot(QMediaPlayer.Error)
    def _on_player_error(self, error):
        error_string = self.player.errorString()
        if error != QMediaPlayer.NoError:
            logger.error(f"QMediaPlayer Error #{error}: {error_string}")
            QMessageBox.warning(self, "Playback Error",
                                f"Could not play the video.\n\nError ({error}):\n{error_string}")
            self.stop()

    def _reset_ui(self):
        self.slider.blockSignals(True)
        self.slider.setValue(0)
        self.slider.blockSignals(False)
        self.slider.setEnabled(False)
        self.lbl_time.setText("0:00 / 0:00")
        self._last_position = 0

    def _fmt(self, ms):
        if ms < 0: ms = 0
        s = int(ms / 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def resizeEvent(self, e):
        self._reposition_overlays()
        super().resizeEvent(e)

    def _reposition_overlays(self):
        video_rect = self.video.geometry()
        self.thumbnail_label.setGeometry(video_rect)
        self.big_play.setGeometry(
            int(video_rect.x() + (video_rect.width() - 96) / 2),
            int(video_rect.y() + (video_rect.height() - 96) / 2),
            96, 96
        )
        self.big_play.raise_()
        bar_height = 56
        r = self.rect()
        self.bar.setGeometry(0, r.height() - bar_height, r.width(), bar_height)
        self.bar.raise_()

    def mouseMoveEvent(self, e):
        self._mouse_active = True
        self.show_controls(True)
        self.start_auto_hide()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        self._mouse_active = False
        self.start_auto_hide()
        super().leaveEvent(e)

    def start_auto_hide(self):
        self.bar_timer.stop()
        if self.player.state() == QMediaPlayer.PlayingState:
            self.bar_timer.start()

    def _maybe_hide_controls(self):
        if (self.player.state() == QMediaPlayer.PlayingState
                and not self._mouse_active and self._controls_visible):
            self.show_controls(False)
        self._mouse_active = False

    def show_controls(self, show: bool):
        self.bar.setVisible(show)
        self._controls_visible = show
        self.setCursor(Qt.ArrowCursor if show else Qt.BlankCursor)
        if show:
            self.bar.raise_()

    def mouseDoubleClickEvent(self, e):
        self.doubleClicked.emit()
        e.accept()

    def toggle_fullscreen(self):
        vw = self.window()
        if vw:
            if not vw.isFullScreen():
                vw.showFullScreen()
            else:
                vw.showNormal()

    def keyPressEvent(self, e):
        key = e.key()
        if key == Qt.Key_Space: self.toggle_play(); return
        if key == Qt.Key_Right and self.player.isSeekable():
            self.player.setPosition(self.player.position() + 5000); return
        if key == Qt.Key_Left and self.player.isSeekable():
            self.player.setPosition(max(0, self.player.position() - 5000)); return
        if key == Qt.Key_F: self.toggle_fullscreen(); return
        if key == Qt.Key_M: self._toggle_mute(); return
        super().keyPressEvent(e)


# ══════════════════════════════════════════════════════════════════
#   Camera Stream Tile
# ══════════════════════════════════════════════════════════════════

class CameraStreamTile(QWidget):
    doubleClicked = pyqtSignal()

    def __init__(self, api: APIClient, camera_name: str, parent=None):
        super().__init__(parent)
        self.api = api
        self.camera_name = camera_name
        self.mode = "sub"
        self.ws_player: Optional[MJPGWebSocketPlayer] = None

        self.setStyleSheet(f"""
            CameraStreamTile {{
                background: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)

        # ── Drop shadow on tile ───────────────────────────────────
        apply_shadow(self, blur=18, offset_y=4, color=Colors.SHADOW_MED)

        self.video = QLabel()
        self.video.setAlignment(Qt.AlignCenter)
        self.video.setStyleSheet(CAMERA_TILE_VIDEO_STYLE)
        self.video.installEventFilter(self)

        self.title = QLabel(f"📹 {camera_name}")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet(CAMERA_TILE_TITLE_STYLE)

        self.btn_toggle = QPushButton("Main / Sub")
        self.btn_toggle.setFixedHeight(28)
        self.btn_toggle.setObjectName("secondaryBtn")
        self.btn_toggle.clicked.connect(self.toggle_quality)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addWidget(self.video, 1)
        lay.addWidget(self.title)
        lay.addWidget(self.btn_toggle)
        lay.setSpacing(4)

        QTimer.singleShot(10, self.start_play)

    def eventFilter(self, source, event):
        if source is self.video and event.type() == QEvent.MouseButtonDblClick:
            self.doubleClicked.emit()
            return True
        return super().eventFilter(source, event)

    def start_play(self):
        self.stop_play()
        try:
            self.api.set_preview_mode(self.camera_name, self.mode)
        except Exception as e:
            logger.warning(f"Failed to set preview mode: {e}")
        try:
            cams = self.api.list_cameras()
            cam = next((c for c in cams if c.get("camera_name") == self.camera_name), None)
            if cam and cam.get("url2") and self.mode == "sub":
                logger.info(f"Using url2 for {self.camera_name}")
        except Exception:
            pass
        self.ws_player = MJPGWebSocketPlayer(self.api, self.camera_name, self._on_frame)
        self.ws_player.start()

    def stop_play(self):
        if self.ws_player:
            try: self.ws_player.stop()
            except Exception: pass
        self.ws_player = None
        pix = QPixmap(self.video.size())
        pix.fill(Qt.black)
        self.video.setPixmap(pix)

    def toggle_quality(self):
        self.mode = "sub" if self.mode == "main" else "main"
        self.title.setText(f"{self.camera_name} ({self.mode.upper()})")
        self.start_play()

    def _on_frame(self, rgb_np, text_msg=None):
        if text_msg: self.title.setToolTip(text_msg); return
        if rgb_np is None: return
        h, w, ch = rgb_np.shape
        img = QImage(rgb_np.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(self.video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video.setPixmap(pix)

    def closeEvent(self, e: QCloseEvent):
        try: self.stop_play()
        except Exception: pass
        super().closeEvent(e)


# ══════════════════════════════════════════════════════════════════
#   Splash Screen — Monochrome with light glow
# ══════════════════════════════════════════════════════════════════

class SplashScreen(QSplashScreen):
    def __init__(self):
        pixmap = QPixmap(540, 340)
        pixmap.fill(QColor(Colors.BG_DARKEST))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # ── Background gradient (dark to darker) ──────────────────
        grad = QLinearGradient(0, 0, pixmap.width(), pixmap.height())
        grad.setColorAt(0, QColor("#0e0e0e"))
        grad.setColorAt(0.5, QColor("#141414"))
        grad.setColorAt(1, QColor("#0a0a0a"))
        painter.fillRect(pixmap.rect(), grad)

        # ── Subtle white glow circle (center) ─────────────────────
        glow = QRadialGradient(pixmap.width() / 2, pixmap.height() / 2, 200)
        glow.setColorAt(0, QColor(255, 255, 255, 14))
        glow.setColorAt(0.5, QColor(255, 255, 255, 6))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(pixmap.width()/2 - 200), int(pixmap.height()/2 - 200), 400, 400)

        # ── Fine grid pattern overlay (subtle texture) ────────────
        painter.setPen(QColor(255, 255, 255, 6))
        for x in range(0, pixmap.width(), 20):
            painter.drawLine(x, 0, x, pixmap.height())
        for y in range(0, pixmap.height(), 20):
            painter.drawLine(0, y, pixmap.width(), y)

        # ── Logo ──────────────────────────────────────────────────
        if os.path.exists(LOGO_PATH):
            logo_pix = QPixmap(LOGO_PATH).scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(int(pixmap.width()/2 - logo_pix.width()/2), 35, logo_pix)

        # ── Title (white) ─────────────────────────────────────────
        painter.setPen(QColor("#f0f0f0"))
        painter.setFont(QFont("Segoe UI", 24, QFont.Bold))
        painter.drawText(pixmap.rect().adjusted(0, 95, 0, 0), Qt.AlignCenter, "DEEP BLUE CCTV")

        # ── Subtitle ──────────────────────────────────────────────
        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor("#777777"))
        painter.drawText(pixmap.rect().adjusted(0, 145, 0, 0), Qt.AlignCenter, "Ultimate Grid Edition  •  v2.0")

        # ── Bottom accent line (monochrome silver gradient) ───────
        painter.setPen(Qt.NoPen)
        accent = QLinearGradient(0, 0, pixmap.width(), 0)
        accent.setColorAt(0, QColor(255, 255, 255, 0))
        accent.setColorAt(0.2, QColor(200, 200, 200, 60))
        accent.setColorAt(0.5, QColor(255, 255, 255, 120))
        accent.setColorAt(0.8, QColor(200, 200, 200, 60))
        accent.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(accent)
        painter.drawRect(0, pixmap.height() - 2, pixmap.width(), 2)

        # ── Top accent line ───────────────────────────────────────
        top_accent = QLinearGradient(0, 0, pixmap.width(), 0)
        top_accent.setColorAt(0, QColor(255, 255, 255, 0))
        top_accent.setColorAt(0.5, QColor(255, 255, 255, 30))
        top_accent.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(top_accent)
        painter.drawRect(0, 0, pixmap.width(), 1)

        painter.end()

        super().__init__(pixmap)
        self.showMessage("Initializing...", Qt.AlignCenter | Qt.AlignBottom, QColor(SPLASH_MSG_COLOR))

        self.dot_count = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_dots)
        self.timer.start(400)

    def _update_dots(self):
        self.dot_count = (self.dot_count + 1) % 4
        dots = "•" * self.dot_count + " " * (3 - self.dot_count)
        self.showMessage(f"  Loading {dots}", Qt.AlignCenter | Qt.AlignBottom, QColor(SPLASH_MSG_COLOR))

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)
