"""
auth_dialogs.py — Login, Change Password, Register, and Temp Password dialogs.
Premium monochrome design with shadow effects and animations.
"""
from config import *
from theme import *
from api_client import APIClient


# ══════════════════════════════════════════════════════════════════
#   Login Dialog — Glassmorphism Card
# ══════════════════════════════════════════════════════════════════

class DeepBlueLoginDialog(QDialog):
    def __init__(self, api: APIClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Login — AI-CCTV")
        self.setFixedSize(420, 560)
        self.setStyleSheet(LOGIN_STYLESHEET)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(0)

        # ── Logo ──────────────────────────────────────────────────
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        if os.path.exists(LOGO_PATH):
            logo_pix = QPixmap(LOGO_PATH).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pix)
        else:
            logo_label.setText("🔒")
            logo_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(logo_label)
        layout.addSpacing(12)

        # ── Title ─────────────────────────────────────────────────
        title = QLabel("AI-CCTV")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(4)

        subtitle = QLabel("Surveillance Management System")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(28)

        # ── Form ──────────────────────────────────────────────────
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("👤  Username")
        self.txt_user.setFixedHeight(44)
        layout.addWidget(self.txt_user)
        layout.addSpacing(12)

        self.txt_pass = QLineEdit()
        self.txt_pass.setPlaceholderText("🔑  Password")
        self.txt_pass.setEchoMode(QLineEdit.Password)
        self.txt_pass.setFixedHeight(44)
        layout.addWidget(self.txt_pass)
        layout.addSpacing(12)

        self.chk_remember = QCheckBox("Remember this session")
        layout.addWidget(self.chk_remember)
        layout.addSpacing(20)

        # ── Login Button ──────────────────────────────────────────
        self.btn_login = QPushButton("Sign In")
        self.btn_login.setObjectName("loginBtn")
        self.btn_login.setFixedHeight(48)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_login)
        layout.addSpacing(12)

        # ── Temp Login Button ─────────────────────────────────────
        self.btn_temp = QPushButton("Use Temporary Password")
        self.btn_temp.setObjectName("secondaryBtn")
        self.btn_temp.setFixedHeight(38)
        self.btn_temp.setStyleSheet(f"""
            QPushButton#secondaryBtn {{
                background: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                font-weight: 500;
            }}
            QPushButton#secondaryBtn:hover {{
                color: {Colors.PRIMARY};
                border: 1px solid {Colors.PRIMARY};
                background: {Colors.PRIMARY_BG};
            }}
        """)
        self.btn_temp.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_temp)

        layout.addStretch(1)

        # ── Status ────────────────────────────────────────────────
        self.msg = QLabel("")
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setWordWrap(True)
        self.msg.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
        layout.addWidget(self.msg)

        # ── Connections ───────────────────────────────────────────
        self.btn_login.clicked.connect(self.handle_login)
        self.txt_pass.returnPressed.connect(self.handle_login)
        self.txt_user.returnPressed.connect(lambda: self.txt_pass.setFocus())
        self.btn_temp.clicked.connect(self.handle_temp_login)

        # ── Visual Effects ────────────────────────────────────────
        apply_shadow(self.btn_login, blur=22, offset_y=3, color=QColor(0, 0, 0, 100))
        apply_shadow(logo_label, blur=30, offset_y=0, color=QColor(255, 255, 255, 25))

        self._try_auto_login()

    def showEvent(self, event):
        """Fade-in dialog on open."""
        super().showEvent(event)
        animate_dialog_open(self, duration=350)

    def _try_auto_login(self):
        """Attempt auto-login from saved config."""
        try:
            config = self.api.load_config()
            if config and config.get("token"):
                logger.info("Found saved session, verifying...")
                self.msg.setStyleSheet(f"color: {Colors.PRIMARY}; font-size: 12px;")
                self.msg.setText("Restoring previous session...")
                QApplication.processEvents()
                try:
                    r = self.api._get("/cameras")
                    if r.status_code == 200:
                        self.accept()
                        return
                    else:
                        self.api.clear_config()
                        self.msg.setText("")
                except Exception:
                    self.api.clear_config()
                    self.msg.setText("")
        except Exception:
            pass

    def handle_login(self):
        username = self.txt_user.text().strip()
        password = self.txt_pass.text()
        remember = self.chk_remember.isChecked()

        if not username or not password:
            self.msg.setStyleSheet(f"color: {Colors.WARNING}; font-size: 12px;")
            self.msg.setText("กรุณากรอก Username และ Password")
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("Signing in...")
        self.msg.setStyleSheet(f"color: {Colors.PRIMARY}; font-size: 12px;")
        self.msg.setText("Authenticating...")
        QApplication.processEvents()

        try:
            self.api.login(username, password, remember=remember)
            if remember:
                self.api.save_config()
            self.accept()

        except RuntimeError as e:
            err_str = str(e)
            if "already logged in" in err_str.lower() or "active_session" in err_str.lower():
                reply = QMessageBox.question(
                    self, "Active Session",
                    "บัญชีนี้กำลังเข้าสู่ระบบอยู่ที่อื่น\nต้องการบังคับเข้าสู่ระบบใหม่หรือไม่?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    try:
                        self.api.login(username, password, remember=remember, force=True)
                        if remember: self.api.save_config()
                        self.accept()
                        return
                    except Exception as e2:
                        self.msg.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
                        self.msg.setText(str(e2))
                else:
                    self.msg.setStyleSheet(f"color: {Colors.WARNING}; font-size: 12px;")
                    self.msg.setText("Login cancelled")
            else:
                self.msg.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
                self.msg.setText(err_str)
        except Exception as e:
            self.msg.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
            self.msg.setText(str(e))
        finally:
            self.btn_login.setEnabled(True)
            self.btn_login.setText("Sign In")

    def handle_temp_login(self):
        """Prompt for temp password and attempt login."""
        username = self.txt_user.text().strip()
        if not username:
            self.msg.setStyleSheet(f"color: {Colors.WARNING}; font-size: 12px;")
            self.msg.setText("กรุณากรอก Username ก่อน")
            return

        temp_pw, ok = QInputDialog.getText(self, "Temporary Password",
                                           f"กรอกรหัสผ่านชั่วคราวสำหรับ '{username}':",
                                           QLineEdit.Password)
        if not ok or not temp_pw.strip():
            return

        self.btn_temp.setEnabled(False)
        self.msg.setStyleSheet(f"color: {Colors.PRIMARY}; font-size: 12px;")
        self.msg.setText("Verifying temp password...")
        QApplication.processEvents()

        try:
            self.api.login_temp(username, temp_pw.strip())
            QMessageBox.information(self, "Temp Login",
                                    "เข้าสู่ระบบด้วยรหัสชั่วคราวสำเร็จ\nกรุณาเปลี่ยนรหัสผ่านใหม่ทันที")
            self._force_change_password()
        except Exception as e:
            self.msg.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
            self.msg.setText(f"Temp login failed: {str(e)}")
        finally:
            self.btn_temp.setEnabled(True)

    def _force_change_password(self):
        dlg = ChangePasswordDialog(self.api, self)
        dlg.setWindowTitle("Set New Password (Required)")
        if dlg.exec_() == QDialog.Accepted:
            self.accept()

    def reject(self):
        super().reject()


# ══════════════════════════════════════════════════════════════════
#   Change Password Dialog
# ══════════════════════════════════════════════════════════════════

class ChangePasswordDialog(QDialog):
    def __init__(self, api: APIClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Change Password")
        self.setFixedSize(400, 320)
        self.setStyleSheet(DIALOG_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        # ── Header ────────────────────────────────────────────────
        header = QLabel()
        header.setText(styled_title("🔐 Change Password"))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        desc = QLabel("กรุณาตั้งรหัสผ่านใหม่ที่มีความยาวอย่างน้อย 6 ตัวอักษร")
        desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        layout.addSpacing(8)

        # ── Fields ────────────────────────────────────────────────
        self.new_pw = QLineEdit()
        self.new_pw.setPlaceholderText("New Password")
        self.new_pw.setEchoMode(QLineEdit.Password)
        self.new_pw.setFixedHeight(42)
        layout.addWidget(self.new_pw)

        self.confirm_pw = QLineEdit()
        self.confirm_pw.setPlaceholderText("Confirm New Password")
        self.confirm_pw.setEchoMode(QLineEdit.Password)
        self.confirm_pw.setFixedHeight(42)
        layout.addWidget(self.confirm_pw)
        layout.addSpacing(8)

        # ── Button ────────────────────────────────────────────────
        self.btn_save = QPushButton("Save New Password")
        self.btn_save.setFixedHeight(44)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_save)

        self.msg = QLabel("")
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
        layout.addWidget(self.msg)
        layout.addStretch()

        self.btn_save.clicked.connect(self.handle_save)
        self.confirm_pw.returnPressed.connect(self.handle_save)

    def handle_save(self):
        pw = self.new_pw.text()
        confirm = self.confirm_pw.text()
        if not pw or len(pw) < 6:
            self.msg.setText("รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร")
            return
        if pw != confirm:
            self.msg.setText("รหัสผ่านไม่ตรงกัน")
            return
        try:
            self.api.change_password(pw)
            QMessageBox.information(self, "สำเร็จ", "เปลี่ยนรหัสผ่านเรียบร้อยแล้ว")
            self.accept()
        except Exception as e:
            self.msg.setText(str(e))


# ══════════════════════════════════════════════════════════════════
#   Register User Dialog
# ══════════════════════════════════════════════════════════════════

class RegisterDialog(QDialog):
    def __init__(self, api: APIClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Register New User")
        self.setFixedSize(440, 480)
        self.setStyleSheet(DIALOG_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(10)

        # ── Header ────────────────────────────────────────────────
        header = QLabel()
        header.setText(styled_title("👤 Register New User"))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        layout.addSpacing(12)

        # ── Form ──────────────────────────────────────────────────
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Username")
        self.txt_user.setFixedHeight(40)
        form.addRow("Username:", self.txt_user)

        self.txt_pass = QLineEdit()
        self.txt_pass.setPlaceholderText("Password (min 6 chars)")
        self.txt_pass.setEchoMode(QLineEdit.Password)
        self.txt_pass.setFixedHeight(40)
        form.addRow("Password:", self.txt_pass)

        self.txt_dept = QLineEdit()
        self.txt_dept.setPlaceholderText("e.g., IT, HR, Security")
        self.txt_dept.setFixedHeight(40)
        form.addRow("Department:", self.txt_dept)

        self.txt_access = QLineEdit()
        self.txt_access.setPlaceholderText("e.g., CAM01,CAM02 (comma separated)")
        self.txt_access.setFixedHeight(40)
        form.addRow("Camera Access:", self.txt_access)

        self.chk_admin = QCheckBox("Grant Admin Rights")
        form.addRow("", self.chk_admin)

        layout.addLayout(form)
        layout.addSpacing(16)

        # ── Button ────────────────────────────────────────────────
        self.btn_register = QPushButton("Create Account")
        self.btn_register.setFixedHeight(44)
        self.btn_register.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_register)

        self.msg = QLabel("")
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setWordWrap(True)
        self.msg.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
        layout.addWidget(self.msg)
        layout.addStretch()

        self.btn_register.clicked.connect(self.handle_register)

    def handle_register(self):
        username = self.txt_user.text().strip()
        password = self.txt_pass.text()
        department = self.txt_dept.text().strip()
        access_str = self.txt_access.text().strip()
        is_admin = self.chk_admin.isChecked()

        if not username or not password:
            self.msg.setText("กรุณากรอก Username และ Password")
            return
        if len(password) < 6:
            self.msg.setText("รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร")
            return

        try:
            access = [a.strip() for a in access_str.split(",") if a.strip()]
            self.api.register_user(username, password, department, access, is_admin)
            QMessageBox.information(self, "สำเร็จ", f"สร้างบัญชี '{username}' เรียบร้อยแล้ว")
            self.accept()
        except Exception as e:
            self.msg.setText(str(e))


# ══════════════════════════════════════════════════════════════════
#   Reset Temp Password Dialog
# ══════════════════════════════════════════════════════════════════

class ResetTempPasswordDialog(QDialog):
    def __init__(self, api: APIClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Reset Temporary Password")
        self.setFixedSize(440, 420)
        self.setStyleSheet(DIALOG_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(10)

        header = QLabel()
        header.setText(styled_title("🔑 Temporary Password"))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        desc = QLabel("สร้างรหัสผ่านชั่วคราวสำหรับผู้ใช้ที่ลืมรหัสผ่าน")
        desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Username to reset")
        self.txt_user.setFixedHeight(40)
        form.addRow("Username:", self.txt_user)

        self.txt_temp_pw = QLineEdit()
        self.txt_temp_pw.setPlaceholderText("(Leave blank to auto-generate)")
        self.txt_temp_pw.setFixedHeight(40)
        form.addRow("Temp Password:", self.txt_temp_pw)

        self.spin_expire = QSpinBox()
        self.spin_expire.setRange(5, 1440)
        self.spin_expire.setValue(30)
        self.spin_expire.setSuffix(" minutes")
        form.addRow("Expire After:", self.spin_expire)

        layout.addLayout(form)
        layout.addSpacing(14)

        self.btn_generate = QPushButton("Generate Temp Password")
        self.btn_generate.setFixedHeight(44)
        self.btn_generate.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_generate)
        layout.addSpacing(8)

        # ── Result Box ────────────────────────────────────────────
        self.result_box = QWidget()
        self.result_box.setStyleSheet(f"""
            QWidget {{
                background: {Colors.BG_CARD};
                border: 1px solid {Colors.SUCCESS};
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        rb_layout = QVBoxLayout(self.result_box)
        self.result_label = QLabel("")
        self.result_label.setStyleSheet(f"""
            font-size: 20px; font-weight: 600;
            color: {Colors.SUCCESS}; font-family: 'Consolas', monospace;
        """)
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        rb_layout.addWidget(self.result_label)

        self.btn_copy = QPushButton("📋 Copy to Clipboard")
        self.btn_copy.setFixedHeight(36)
        self.btn_copy.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {Colors.PRIMARY_BG};
                border: 1px solid {Colors.PRIMARY};
            }}
        """)
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        rb_layout.addWidget(self.btn_copy)
        self.result_box.hide()
        layout.addWidget(self.result_box)

        self.msg = QLabel("")
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
        layout.addWidget(self.msg)
        layout.addStretch()

        self.btn_generate.clicked.connect(self.handle_generate)
        self.btn_copy.clicked.connect(self._copy_result)

    def handle_generate(self):
        username = self.txt_user.text().strip()
        if not username:
            self.msg.setText("กรุณากรอก Username")
            return

        temp_pw = self.txt_temp_pw.text().strip() or None
        expire = self.spin_expire.value()

        self.btn_generate.setEnabled(False)
        self.msg.setStyleSheet(f"color: {Colors.PRIMARY}; font-size: 12px;")
        self.msg.setText("Generating...")
        QApplication.processEvents()

        try:
            result = self.api.admin_reset_temp_password(username, expire, temp_pw)
            generated = result.get("temp_password", temp_pw or "???")
            self.result_label.setText(generated)
            self.result_box.show()
            self.msg.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 12px;")
            self.msg.setText(f"✅ Temp password set for '{username}' (expires in {expire} min)")
        except Exception as e:
            self.result_box.hide()
            self.msg.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
            self.msg.setText(str(e))
        finally:
            self.btn_generate.setEnabled(True)

    def _copy_result(self):
        text = self.result_label.text()
        if text:
            QApplication.clipboard().setText(text)
            self.btn_copy.setText("✅ Copied!")
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 Copy to Clipboard"))
