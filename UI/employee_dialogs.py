"""
employee_dialogs.py — Add, Delete, Edit Employee dialogs.
"""
from config import *
from theme import *
from api_client import APIClient


# ══════════════════════════════════════════════════════════════════
#   Add Employee Dialog
# ══════════════════════════════════════════════════════════════════

class AddEmployeeDialog(QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Enroll Employee")
        self.setMinimumWidth(520)
        self.setStyleSheet(DIALOG_STYLESHEET)

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 20, 28, 20)
        v.setSpacing(10)

        header = QLabel()
        header.setText(styled_title("👤 Enroll New Employee"))
        header.setAlignment(Qt.AlignCenter)
        v.addWidget(header)
        v.addSpacing(8)

        form = QFormLayout()
        form.setSpacing(10)

        self.emp_id = QLineEdit()
        self.emp_id.setPlaceholderText("Employee ID")
        self.emp_id.setFixedHeight(38)
        form.addRow("Employee ID:", self.emp_id)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Full Name")
        self.name.setFixedHeight(38)
        form.addRow("Name:", self.name)

        self.department = QComboBox()
        initial_departments = ["(พิมพ์เพื่อเพิ่ม)", "IT", "HR", "Finance", "Security"]
        self.department.addItems(initial_departments)
        self.department.setEditable(True)
        self.department.lineEdit().setPlaceholderText("เลือกหรือพิมพ์แผนกใหม่...")
        self.department.currentTextChanged.connect(
            lambda t: self.department.lineEdit().setText("") if t == "(พิมพ์เพื่อเพิ่ม)" else None)
        form.addRow("Department:", self.department)

        # ── Image Gallery ─────────────────────────────────────────
        self.image_paths = []
        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setIconSize(QSize(100, 100))
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setWordWrap(True)
        self.image_list.setMinimumHeight(130)
        self.image_list.setMaximumHeight(150)
        self.image_list.setStyleSheet(f"""
            QListWidget {{
                background: {Colors.BG_INPUT};
                border: 2px dashed {Colors.BORDER};
                border-radius: 10px;
            }}
            QListWidget::item {{
                border-radius: 6px;
                padding: 4px;
            }}
            QListWidget::item:selected {{
                background: {Colors.PRIMARY_BG};
                border: 1px solid {Colors.PRIMARY};
            }}
        """)
        form.addRow("Images:", self.image_list)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("📷 Select Images (Max 5)")
        self.add_btn.setObjectName("secondaryBtn")
        self.add_btn.clicked.connect(self.choose_images)
        btn_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("❌ Remove Selected")
        self.remove_btn.setObjectName("deleteBtn")
        self.remove_btn.clicked.connect(self.remove_selected_image)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addStretch()
        form.addRow("", btn_layout)

        v.addLayout(form)
        v.addStretch(1)

        self.submit_btn = QPushButton("✅ Enroll Employee")
        self.submit_btn.setFixedHeight(44)
        self.submit_btn.setCursor(Qt.PointingHandCursor)
        self.submit_btn.clicked.connect(self.submit)
        v.addWidget(self.submit_btn)

        self.msg = QLabel("")
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
        v.addWidget(self.msg)

    def choose_images(self):
        current_count = len(self.image_paths)
        if current_count >= 5:
            QMessageBox.warning(self, "Limit Reached", "You can only add a maximum of 5 images.")
            return
        remaining = 5 - current_count
        paths, _ = QFileDialog.getOpenFileNames(self, f"Select Images (Up to {remaining} more)", "",
                                                "Images (*.jpg *.jpeg *.png)")
        if not paths: return
        paths_to_add = paths
        if len(paths) > remaining:
            QMessageBox.warning(self, "Limit Exceeded",
                                f"Only {remaining} slots available.\nFirst {remaining} images will be added.")
            paths_to_add = paths[:remaining]
        self.image_paths.extend(paths_to_add)
        for path in paths_to_add:
            filename = os.path.basename(path)
            pixmap = QPixmap(path).scaled(QSize(100, 100), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item = QListWidgetItem(filename)
            item.setIcon(QIcon(pixmap))
            self.image_list.addItem(item)
        if len(self.image_paths) >= 5:
            self.add_btn.setEnabled(False)
            self.add_btn.setText("Image slots are full (5/5)")

    def remove_selected_image(self):
        current_item = self.image_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select an image to remove.")
            return
        ret = QMessageBox.question(self, "Confirm Remove",
                                   f"Remove '{current_item.text()}' ?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret == QMessageBox.Yes:
            row = self.image_list.row(current_item)
            self.image_list.takeItem(row)
            if 0 <= row < len(self.image_paths):
                self.image_paths.pop(row)
            if len(self.image_paths) < 5:
                self.add_btn.setEnabled(True)
                self.add_btn.setText("📷 Select Images (Max 5)")

    def submit(self):
        emp_id = self.emp_id.text().strip()
        name = self.name.text().strip()
        department = self.department.currentText().strip()
        if not (emp_id and name and department and self.image_paths):
            self.msg.setText("Please fill in all fields and add at least one image")
            return
        try:
            self.api.enroll_employee(emp_id, name, department, self.image_paths)
            QMessageBox.information(self, "Success", "Employee enrolled successfully")
            self.accept()
        except Exception as e:
            self.msg.setText(f"Error: {e}")


# ══════════════════════════════════════════════════════════════════
#   Delete Employee Dialog
# ══════════════════════════════════════════════════════════════════

class DeleteEmployeeDialog(QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Delete Employee")
        self.setFixedSize(380, 220)
        self.setStyleSheet(DIALOG_STYLESHEET)

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 20, 28, 20)
        v.setSpacing(12)

        header = QLabel()
        header.setText(styled_title("⚠️ Delete Employee"))
        header.setAlignment(Qt.AlignCenter)
        v.addWidget(header)

        desc = QLabel("เมื่อลบแล้วจะไม่สามารถกู้คืนได้ข้อมูลใบหน้าทั้งหมดจะถูกลบ")
        desc.setStyleSheet(f"color: {Colors.DANGER}; font-size: 12px;")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        v.addWidget(desc)

        form = QFormLayout()
        self.emp_id = QLineEdit()
        self.emp_id.setPlaceholderText("Employee ID")
        self.emp_id.setFixedHeight(40)
        form.addRow("Employee ID:", self.emp_id)
        v.addLayout(form)

        self.btn = QPushButton("🗑️ Delete Employee")
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
        emp_id = self.emp_id.text().strip()
        if not emp_id: self.msg.setText("Please enter employee ID"); return
        try:
            self.api.delete_employee(emp_id)
            QMessageBox.information(self, "Success", f"Employee {emp_id} deleted successfully")
            self.accept()
        except Exception as e:
            self.msg.setText(f"Error: {e}")


# ══════════════════════════════════════════════════════════════════
#   Edit Employee Dialog
# ══════════════════════════════════════════════════════════════════

class EditEmployeeDialog(QDialog):
    employeeUpdated = pyqtSignal()

    def __init__(self, api: APIClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.current_emp_id: Optional[str] = None
        self.current_emp_data: Optional[dict] = None

        self.setWindowTitle("Edit Employee Information")
        self.setMinimumSize(740, 500)
        self.setStyleSheet(DIALOG_STYLESHEET + f"""
            QLabel#slotLabel {{
                background: {Colors.BG_INPUT};
                border: 2px dashed {Colors.BORDER};
                border-radius: 8px;
                min-height: 100px; max-height: 100px;
                min-width: 100px; max-width: 100px;
                color: {Colors.TEXT_DISABLED};
                font-size: 11px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(10)

        header = QLabel()
        header.setText(styled_title("✏️ Edit Employee"))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        layout.addSpacing(4)

        # ── 1. Employee selector (searchable) ─────────────────────
        form_layout = QFormLayout()
        self.emp_select = QComboBox()
        self.emp_select.setEditable(True)
        self.emp_select.lineEdit().setPlaceholderText("Loading employees...")
        self.emp_select.setEnabled(False)

        self.completer = QCompleter(self)
        self.completer_model = QStringListModel()
        self.completer.setModel(self.completer_model)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.emp_select.setCompleter(self.completer)
        form_layout.addRow("Select Employee:", self.emp_select)
        layout.addLayout(form_layout)

        # ── 2. Info group ─────────────────────────────────────────
        self.info_groupbox = QGroupBox("Employee Information")
        info_layout = QFormLayout(self.info_groupbox)
        info_layout.setSpacing(8)

        self.emp_id_label = QLineEdit()
        self.emp_id_label.setReadOnly(True)
        self.name_edit = QLineEdit()
        self.name_edit.setFixedHeight(38)
        self.department_edit = QComboBox()
        self.department_edit.setEditable(True)
        initial_departments = ["(พิมพ์เพื่อเพิ่ม)", "IT", "HR", "Finance", "Security"]
        self.department_edit.addItems(initial_departments)
        info_layout.addRow("Employee ID:", self.emp_id_label)
        info_layout.addRow("Full Name:", self.name_edit)
        info_layout.addRow("Department:", self.department_edit)
        layout.addWidget(self.info_groupbox)

        # ── 3. Image slots ────────────────────────────────────────
        self.slots_groupbox = QGroupBox("Image Slots (Max 5)")
        self.slots_layout = QGridLayout(self.slots_groupbox)
        self.slots_layout.setSpacing(10)
        for i in range(1, 6):
            slot_widget = QWidget()
            slot_vbox = QVBoxLayout(slot_widget)
            slot_vbox.setContentsMargins(0, 0, 0, 0)
            slot_vbox.setSpacing(4)

            img_label = QLabel(f"Slot {i}\n(Empty)")
            img_label.setObjectName("slotLabel")
            img_label.setAlignment(Qt.AlignCenter)
            setattr(self, f"slot_img_{i}", img_label)
            slot_vbox.addWidget(img_label)

            add_btn = QPushButton("➕ Add")
            add_btn.setObjectName("secondaryBtn")
            add_btn.setFixedHeight(28)
            add_btn.clicked.connect(lambda _, s=i: self._on_add_image(s))
            setattr(self, f"slot_add_btn_{i}", add_btn)
            slot_vbox.addWidget(add_btn)

            del_btn = QPushButton("❌ Delete")
            del_btn.setObjectName("deleteBtn")
            del_btn.setFixedHeight(28)
            del_btn.clicked.connect(lambda _, s=i: self._on_delete_slot(s))
            setattr(self, f"slot_del_btn_{i}", del_btn)
            slot_vbox.addWidget(del_btn)

            self.slots_layout.addWidget(slot_widget, 0, i - 1)
        layout.addWidget(self.slots_groupbox)

        # ── 4. Save button ────────────────────────────────────────
        self.submit_btn = QPushButton("💾 Save Info Changes (Name/Dept)")
        self.submit_btn.setFixedHeight(42)
        self.submit_btn.setCursor(Qt.PointingHandCursor)
        self.submit_btn.clicked.connect(self.submit_info_only)
        layout.addWidget(self.submit_btn)

        self.msg = QLabel("")
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(self.msg)
        layout.addStretch(1)

        # ── Hide until selected ───────────────────────────────────
        self.info_groupbox.hide()
        self.slots_groupbox.hide()
        self.submit_btn.hide()

        self.emp_select.activated.connect(self.on_employee_selected)
        QTimer.singleShot(100, self.load_employees)

    def load_employees(self):
        try:
            employees = self.api.list_employees()
            self.emp_select.clear()
            self.completer_model.setStringList([])
            self.emp_select.addItem("", None)
            employee_list = []
            for emp in employees:
                emp_name = emp.get("full_name") or "Unnamed"
                emp_id = emp.get("emp_id")
                display = f"{emp_name} ({emp_id})"
                self.emp_select.addItem(display, emp_id)
                employee_list.append(display)
            self.completer_model.setStringList(employee_list)
            self.emp_select.setEnabled(True)
            self.emp_select.lineEdit().setPlaceholderText("Type to search employee...")
            self.msg.setText("Please select an employee to edit.")
        except Exception as e:
            self.emp_select.lineEdit().setPlaceholderText("Failed to load employees.")
            self.msg.setText(f"Error loading: {e}")

    def on_employee_selected(self, index):
        self.current_emp_id = self.emp_select.itemData(index)
        if not self.current_emp_id:
            self.info_groupbox.hide()
            self.slots_groupbox.hide()
            self.submit_btn.hide()
            self.current_emp_data = None
            return
        self.info_groupbox.show()
        self.slots_groupbox.show()
        self.submit_btn.show()
        self.refresh_employee_details()

    def refresh_employee_details(self):
        if not self.current_emp_id: return
        try:
            self.msg.setText("Loading details...")
            QApplication.processEvents()
            data = self.api.get_employee_details(self.current_emp_id)
            self.current_emp_data = data
            self.emp_id_label.setText(data.get("emp_id", ""))
            self.name_edit.setText(data.get("full_name", ""))
            dept = data.get("department", "")
            if dept:
                idx = self.department_edit.findText(dept)
                if idx == -1:
                    self.department_edit.addItem(dept)
                    self.department_edit.setCurrentText(dept)
                else:
                    self.department_edit.setCurrentIndex(idx)
            else:
                self.department_edit.setCurrentIndex(0)
            slots_data = data.get("slots", {})
            for i in range(1, 6):
                img_label = getattr(self, f"slot_img_{i}")
                add_btn = getattr(self, f"slot_add_btn_{i}")
                del_btn = getattr(self, f"slot_del_btn_{i}")
                img_b64 = slots_data.get(str(i))
                if img_b64:
                    try:
                        pixmap = QPixmap()
                        pixmap.loadFromData(base64.b64decode(img_b64), "JPG")
                        img_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        del_btn.show(); add_btn.hide()
                    except Exception as e:
                        logger.error(f"Error decoding base64 for slot {i}: {e}")
                        img_label.setText(f"Slot {i}\n(Load Error)")
                        del_btn.show(); add_btn.hide()
                else:
                    img_label.setText(f"Slot {i}\n(Empty)")
                    img_label.setPixmap(QPixmap())
                    del_btn.hide(); add_btn.show()
            self.msg.setText("Employee details loaded.")
        except Exception as e:
            self.msg.setText(f"Error loading details: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load details:\n{str(e)}")

    def _on_delete_slot(self, slot_num: int):
        if not self.current_emp_id: return
        ret = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete Slot {slot_num} for {self.current_emp_id}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if ret == QMessageBox.Yes:
            try:
                self.msg.setText(f"Deleting slot {slot_num}...")
                QApplication.processEvents()
                self.api.delete_employee_slot(self.current_emp_id, slot_num)
                self.msg.setText(f"Slot {slot_num} deleted. Refreshing...")
                self.refresh_employee_details()
            except Exception as e:
                self.msg.setText(f"Error deleting slot: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete slot:\n{str(e)}")

    def _on_add_image(self, slot_num: int):
        if not self.current_emp_id: return
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.jpg *.jpeg *.png)")
        if not path: return
        try:
            self.msg.setText("Adding new image...")
            QApplication.processEvents()
            self.api.update_employee(
                emp_id=self.current_emp_id,
                name=self.name_edit.text(),
                department=self.department_edit.currentText(),
                image_paths=[path]
            )
            self.msg.setText("New image added. Refreshing...")
            self.refresh_employee_details()
        except Exception as e:
            self.msg.setText(f"Error adding image: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add image:\n{str(e)}")

    def submit_info_only(self):
        if not self.current_emp_id: return
        new_name = self.name_edit.text().strip()
        new_dept = self.department_edit.currentText().strip()
        if not new_name:
            QMessageBox.warning(self, "Error", "Full Name cannot be empty.")
            return
        if new_dept == "(พิมพ์เพื่อเพิ่ม)": new_dept = ""
        try:
            self.msg.setText("Saving info changes...")
            QApplication.processEvents()
            self.api.update_employee_info(self.current_emp_id, new_name, new_dept)
            self.msg.setText("Information saved.")
            QMessageBox.information(self, "Success", "Employee information updated.")
            self.load_employees()
            self.emp_select.setCurrentText(f"{new_name} ({self.current_emp_id})")
        except Exception as e:
            self.msg.setText(f"Error saving info: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save info:\n{str(e)}")
