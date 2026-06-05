"""
theme.py — Premium Monochrome (White/Gray/Black) Design System
with shadow effects and animation utilities for AI-CCTV Client.
"""
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QWidget, QDialog
from PyQt5.QtCore import (QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
                          QSequentialAnimationGroup, QPoint, QSize, QRect, Qt, QTimer)
from PyQt5.QtGui import QColor


# ══════════════════════════════════════════════════════════════════
#                     COLOR PALETTE — MONOCHROME
# ══════════════════════════════════════════════════════════════════

class Colors:
    """Premium Monochrome palette — White / Gray / Black with subtle accent."""

    # ── Backgrounds ───────────────────────────────────────────────
    BG_DARKEST   = "#111111"     # Deepest black
    BG_DARK      = "#1a1a1a"     # Dark surface
    BG_CARD      = "#222222"     # Cards / panels
    BG_ELEVATED  = "#2c2c2c"     # Elevated elements
    BG_INPUT     = "#1e1e1e"     # Input fields

    # ── Light variants (for contrast panels) ──────────────────────
    BG_LIGHT     = "#f5f5f5"     # Light background
    BG_WHITE     = "#ffffff"     # Pure white

    # ── Borders ───────────────────────────────────────────────────
    BORDER       = "#333333"     # Default border
    BORDER_HOVER = "#555555"     # Hover border
    BORDER_FOCUS = "#888888"     # Focus ring
    BORDER_LIGHT = "#e0e0e0"     # Light border

    # ── Primary (White/Silver accent) ─────────────────────────────
    PRIMARY         = "#ffffff"
    PRIMARY_HOVER   = "#e0e0e0"
    PRIMARY_PRESSED = "#cccccc"
    PRIMARY_GLOW    = "rgba(255, 255, 255, 0.12)"
    PRIMARY_BG      = "rgba(255, 255, 255, 0.06)"

    # ── Accent (Subtle warm gray) ─────────────────────────────────
    ACCENT          = "#a0a0a0"
    ACCENT_HOVER    = "#b8b8b8"
    ACCENT_BG       = "rgba(160, 160, 160, 0.10)"

    # ── Semantic ──────────────────────────────────────────────────
    SUCCESS         = "#4caf50"
    SUCCESS_BG      = "rgba(76, 175, 80, 0.12)"
    WARNING         = "#ff9800"
    WARNING_BG      = "rgba(255, 152, 0, 0.12)"
    DANGER          = "#f44336"
    DANGER_HOVER    = "#ef5350"
    DANGER_BG       = "rgba(244, 67, 54, 0.10)"

    # ── Text ──────────────────────────────────────────────────────
    TEXT_PRIMARY   = "#f0f0f0"     # Bright white text
    TEXT_SECONDARY = "#999999"     # Muted gray
    TEXT_DISABLED  = "#555555"     # Dim text
    TEXT_INVERSE   = "#111111"     # Dark text (on light bg)
    TEXT_LINK      = "#cccccc"     # Link text

    # ── Gradients ─────────────────────────────────────────────────
    GRAD_PRIMARY = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #444444, stop:1 #222222)"
    GRAD_ACCENT  = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #555555, stop:1 #333333)"
    GRAD_DANGER  = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f44336, stop:1 #c62828)"
    GRAD_SURFACE = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #222222, stop:1 #1a1a1a)"
    GRAD_TOOLBAR = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e1e1e, stop:1 #161616)"
    GRAD_SIDEBAR = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a1a1a, stop:1 #222222)"
    GRAD_SHINE   = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255,255,255,0.06), stop:0.5 rgba(255,255,255,0), stop:1 rgba(0,0,0,0.08))"

    # ── Shadow colors ─────────────────────────────────────────────
    SHADOW_SOFT  = QColor(0, 0, 0, 80)
    SHADOW_MED   = QColor(0, 0, 0, 120)
    SHADOW_HARD  = QColor(0, 0, 0, 180)
    SHADOW_GLOW  = QColor(255, 255, 255, 30)


# ══════════════════════════════════════════════════════════════════
#                   ANIMATION HELPERS
# ══════════════════════════════════════════════════════════════════

def apply_shadow(widget: QWidget, blur: int = 20, offset_x: int = 0,
                 offset_y: int = 4, color: QColor = None):
    """Apply a drop-shadow effect to a widget."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setXOffset(offset_x)
    shadow.setYOffset(offset_y)
    shadow.setColor(color or Colors.SHADOW_MED)
    widget.setGraphicsEffect(shadow)
    return shadow


def apply_glow(widget: QWidget, blur: int = 25, color: QColor = None):
    """Apply a glow (centered shadow) effect to a widget."""
    glow = QGraphicsDropShadowEffect(widget)
    glow.setBlurRadius(blur)
    glow.setXOffset(0)
    glow.setYOffset(0)
    glow.setColor(color or Colors.SHADOW_GLOW)
    widget.setGraphicsEffect(glow)
    return glow


def fade_in(widget: QWidget, duration: int = 400, start_val: float = 0.0,
            end_val: float = 1.0):
    """Fade-in animation using windowOpacity."""
    widget.setWindowOpacity(start_val)
    anim = QPropertyAnimation(widget, b"windowOpacity")
    anim.setDuration(duration)
    anim.setStartValue(start_val)
    anim.setEndValue(end_val)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.start()
    # prevent garbage collection
    widget._fade_anim = anim
    return anim


def slide_in(widget: QWidget, direction: str = "up", distance: int = 30,
             duration: int = 350):
    """Slide-in animation from a direction: up, down, left, right."""
    start_pos = widget.pos()
    offsets = {
        "up": QPoint(0, distance),
        "down": QPoint(0, -distance),
        "left": QPoint(distance, 0),
        "right": QPoint(-distance, 0),
    }
    offset = offsets.get(direction, QPoint(0, distance))
    widget.move(start_pos + offset)
    anim = QPropertyAnimation(widget, b"pos")
    anim.setDuration(duration)
    anim.setStartValue(start_pos + offset)
    anim.setEndValue(start_pos)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.start()
    widget._slide_anim = anim
    return anim


def animate_dialog_open(dialog: QDialog, duration: int = 300):
    """Combined fade + slide animation for dialog opening."""
    dialog.setWindowOpacity(0.0)
    # Fade
    fade = QPropertyAnimation(dialog, b"windowOpacity")
    fade.setDuration(duration)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.OutCubic)
    # Geometry slide-up
    geo = dialog.geometry()
    start_geo = QRect(geo.x(), geo.y() + 20, geo.width(), geo.height())
    end_geo = geo
    slide = QPropertyAnimation(dialog, b"geometry")
    slide.setDuration(duration)
    slide.setStartValue(start_geo)
    slide.setEndValue(end_geo)
    slide.setEasingCurve(QEasingCurve.OutCubic)
    group = QParallelAnimationGroup(dialog)
    group.addAnimation(fade)
    group.addAnimation(slide)
    group.start()
    dialog._open_anim = group
    return group


def pulse_shadow(widget: QWidget, min_blur: int = 8, max_blur: int = 25,
                 duration: int = 1500):
    """Create a pulsing shadow effect (breathing glow)."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(min_blur)
    shadow.setXOffset(0)
    shadow.setYOffset(0)
    shadow.setColor(QColor(255, 255, 255, 35))
    widget.setGraphicsEffect(shadow)

    anim = QPropertyAnimation(shadow, b"blurRadius")
    anim.setDuration(duration)
    anim.setStartValue(min_blur)
    anim.setEndValue(max_blur)
    anim.setEasingCurve(QEasingCurve.InOutSine)
    anim.setLoopCount(-1)  # infinite loop
    # reverse direction
    anim.finished.connect(lambda: None)
    widget._pulse_anim = anim
    widget._pulse_shadow = shadow

    # Use sequential for ping-pong
    seq = QSequentialAnimationGroup(widget)
    fwd = QPropertyAnimation(shadow, b"blurRadius")
    fwd.setDuration(duration)
    fwd.setStartValue(min_blur)
    fwd.setEndValue(max_blur)
    fwd.setEasingCurve(QEasingCurve.InOutSine)
    rev = QPropertyAnimation(shadow, b"blurRadius")
    rev.setDuration(duration)
    rev.setStartValue(max_blur)
    rev.setEndValue(min_blur)
    rev.setEasingCurve(QEasingCurve.InOutSine)
    seq.addAnimation(fwd)
    seq.addAnimation(rev)
    seq.setLoopCount(-1)
    seq.start()
    widget._pulse_seq = seq
    return shadow


# ══════════════════════════════════════════════════════════════════
#                     GLOBAL STYLESHEET
# ══════════════════════════════════════════════════════════════════

C = Colors

GLOBAL_STYLESHEET = f"""
/* ─── Base Window ─────────────────────────────────────────────── */
QMainWindow {{
    background-color: {C.BG_DARKEST};
    font-family: 'Segoe UI', 'Inter', 'Helvetica Neue', sans-serif;
    font-size: 13px;
    color: {C.TEXT_PRIMARY};
}}

/* ─── Toolbar ─────────────────────────────────────────────────── */
QToolBar {{
    background: {C.GRAD_TOOLBAR};
    color: {C.TEXT_PRIMARY};
    padding: 6px 12px;
    spacing: 6px;
    border: none;
    border-bottom: 1px solid {C.BORDER};
}}
QToolButton {{
    background: transparent;
    color: {C.TEXT_SECONDARY};
    padding: 7px 12px;
    border-radius: 6px;
    font-weight: 500;
    border: 1px solid transparent;
    letter-spacing: 0.3px;
}}
QToolButton:hover {{
    background: {C.PRIMARY_BG};
    border: 1px solid {C.BORDER_HOVER};
    color: {C.TEXT_PRIMARY};
}}
QToolButton:pressed {{
    background: rgba(255, 255, 255, 0.1);
}}

/* ─── Splitter ────────────────────────────────────────────────── */
QSplitter::handle {{
    background: {C.BORDER};
    border-radius: 1px;
}}
QSplitter::handle:horizontal {{ width: 3px; margin: 12px 0; }}
QSplitter::handle:vertical   {{ height: 3px; margin: 0 12px; }}
QSplitter::handle:hover {{
    background: {C.BORDER_HOVER};
}}

/* ─── Labels ──────────────────────────────────────────────────── */
QLabel {{
    color: {C.TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Inter', sans-serif;
}}

/* ─── Line Edits ──────────────────────────────────────────────── */
QLineEdit {{
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    padding: 10px 14px;
    background-color: {C.BG_INPUT};
    color: {C.TEXT_PRIMARY};
    font-size: 13px;
    selection-background-color: {C.ACCENT};
}}
QLineEdit:focus {{
    border: 1px solid {C.BORDER_FOCUS};
    background-color: {C.BG_CARD};
}}
QLineEdit::placeholder {{
    color: {C.TEXT_DISABLED};
}}
QLineEdit:read-only {{
    background-color: {C.BG_DARK};
    color: {C.TEXT_SECONDARY};
    border: 1px solid rgba(51,51,51,0.5);
}}

/* ─── ComboBox ────────────────────────────────────────────────── */
QComboBox {{
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    padding: 9px 14px;
    background-color: {C.BG_INPUT};
    color: {C.TEXT_PRIMARY};
    min-height: 18px;
}}
QComboBox:hover {{
    border: 1px solid {C.BORDER_HOVER};
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox QAbstractItemView {{
    background: {C.BG_CARD};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER};
    border-radius: 6px;
    selection-background-color: {C.BG_ELEVATED};
    padding: 4px;
    outline: none;
}}

/* ─── Push Buttons ────────────────────────────────────────────── */
QPushButton {{
    background: {C.GRAD_PRIMARY};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER_HOVER};
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
    font-size: 13px;
    min-height: 16px;
    letter-spacing: 0.3px;
}}
QPushButton:hover {{
    background-color: {C.BG_ELEVATED};
    border: 1px solid {C.BORDER_FOCUS};
    color: {C.PRIMARY};
}}
QPushButton:pressed {{
    background-color: {C.BG_INPUT};
}}
QPushButton:disabled {{
    background-color: {C.BG_DARK};
    color: {C.TEXT_DISABLED};
    border: 1px solid {C.BORDER};
}}

/* ─── Secondary / Clear Button ────────────────────────────────── */
QPushButton#secondaryBtn, QPushButton#clearButton {{
    background: transparent;
    color: {C.TEXT_SECONDARY};
    border: 1px solid {C.BORDER};
}}
QPushButton#secondaryBtn:hover, QPushButton#clearButton:hover {{
    background: {C.PRIMARY_BG};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER_HOVER};
}}

/* ─── Danger Button ───────────────────────────────────────────── */
QPushButton#dangerBtn, QPushButton#deleteBtn {{
    background: {C.GRAD_DANGER};
    color: #ffffff;
    border: none;
}}
QPushButton#dangerBtn:hover, QPushButton#deleteBtn:hover {{
    background-color: {C.DANGER_HOVER};
}}

/* ─── List Widget ─────────────────────────────────────────────── */
QListWidget {{
    background-color: {C.BG_INPUT};
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    color: {C.TEXT_PRIMARY};
    outline: none;
    padding: 4px;
}}
QListWidget::item {{
    padding: 9px 14px;
    border-radius: 6px;
    margin: 1px 0;
    border-bottom: 1px solid rgba(51,51,51,0.3);
}}
QListWidget::item:hover {{
    background-color: {C.BG_ELEVATED};
}}
QListWidget::item:selected {{
    background: {C.PRIMARY_BG};
    border: 1px solid {C.BORDER_HOVER};
    color: {C.TEXT_PRIMARY};
}}

/* ─── Table Widget ────────────────────────────────────────────── */
QTableWidget {{
    gridline-color: rgba(51,51,51,0.5);
    background-color: {C.BG_INPUT};
    alternate-background-color: {C.BG_CARD};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    font-size: 12px;
    selection-background-color: {C.PRIMARY_BG};
}}
QHeaderView::section {{
    background: {C.GRAD_TOOLBAR};
    color: {C.TEXT_PRIMARY};
    padding: 10px 8px;
    font-weight: 600;
    font-size: 12px;
    border: none;
    border-right: 1px solid {C.BORDER};
    border-bottom: 2px solid {C.BORDER_HOVER};
    letter-spacing: 0.3px;
}}

/* ─── Scroll Bars ─────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {C.BG_DARK};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C.BORDER};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C.BORDER_HOVER};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {C.BG_DARK};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {C.BORDER};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {C.BORDER_HOVER};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ─── Status Bar ──────────────────────────────────────────────── */
QStatusBar {{
    background: {C.BG_DARK};
    color: {C.TEXT_SECONDARY};
    border-top: 1px solid {C.BORDER};
    font-size: 12px;
    padding: 2px 10px;
}}

/* ─── GroupBox ─────────────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {C.BORDER};
    border-radius: 10px;
    margin-top: 16px;
    padding: 18px 14px 14px 14px;
    font-weight: 600;
    color: {C.TEXT_PRIMARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 3px 12px;
    color: {C.TEXT_PRIMARY};
    background: {C.GRAD_PRIMARY};
    border: 1px solid {C.BORDER_HOVER};
    border-radius: 6px;
    font-size: 12px;
    letter-spacing: 0.3px;
}}

/* ─── SpinBox / DoubleSpinBox ─────────────────────────────────── */
QSpinBox, QDoubleSpinBox {{
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    padding: 7px 12px;
    background-color: {C.BG_INPUT};
    color: {C.TEXT_PRIMARY};
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {C.BORDER_FOCUS};
}}

/* ─── DateEdit ────────────────────────────────────────────────── */
QDateEdit, QDateTimeEdit {{
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    padding: 9px 14px;
    background-color: {C.BG_INPUT};
    color: {C.TEXT_PRIMARY};
}}
QDateEdit:focus, QDateTimeEdit:focus {{
    border: 1px solid {C.BORDER_FOCUS};
}}

/* ─── CheckBox ────────────────────────────────────────────────── */
QCheckBox {{
    color: {C.TEXT_PRIMARY};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {C.BORDER_HOVER};
    border-radius: 4px;
    background: {C.BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background: {C.TEXT_PRIMARY};
    border-color: {C.TEXT_PRIMARY};
}}
QCheckBox::indicator:hover {{
    border-color: {C.BORDER_FOCUS};
}}

/* ─── Tab Widget ──────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    background: {C.BG_DARK};
}}
QTabBar::tab {{
    background: {C.BG_CARD};
    color: {C.TEXT_SECONDARY};
    padding: 8px 18px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
    border: 1px solid {C.BORDER};
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background: {C.BG_DARK};
    color: {C.TEXT_PRIMARY};
    border-bottom: 2px solid {C.TEXT_PRIMARY};
}}
QTabBar::tab:hover {{
    background: {C.BG_ELEVATED};
    color: {C.TEXT_PRIMARY};
}}

/* ─── Message Box ─────────────────────────────────────────────── */
QMessageBox {{
    background-color: {C.BG_CARD};
}}
QMessageBox QLabel {{
    color: {C.TEXT_PRIMARY};
    font-size: 13px;
    padding: 4px;
}}
QMessageBox QPushButton {{
    background: {C.GRAD_PRIMARY};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER_HOVER};
    padding: 8px 22px;
    border-radius: 8px;
    min-width: 80px;
    font-weight: 600;
}}
QMessageBox QPushButton:hover {{
    background-color: {C.BG_ELEVATED};
    border: 1px solid {C.BORDER_FOCUS};
}}

/* ─── Scroll Area ─────────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* ─── Menu ────────────────────────────────────────────────────── */
QMenu {{
    background: {C.BG_CARD};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 24px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background: {C.PRIMARY_BG};
    color: {C.TEXT_PRIMARY};
}}
QMenu::separator {{
    height: 1px;
    background: {C.BORDER};
    margin: 4px 8px;
}}

/* ─── Slider ──────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 3px;
    background: {C.BORDER};
    border-radius: 1px;
}}
QSlider::handle:horizontal {{
    background: {C.TEXT_PRIMARY};
    border: none;
    border-radius: 7px;
    width: 14px;
    margin: -5px 0;
}}
QSlider::handle:horizontal:hover {{
    background: #ffffff;
    width: 16px;
    margin: -6px 0;
}}
QSlider::groove:horizontal:disabled {{
    background: {C.BG_ELEVATED};
}}
QSlider::handle:horizontal:disabled {{
    background: {C.TEXT_DISABLED};
}}

/* ─── FormLayout Labels ───────────────────────────────────────── */
QFormLayout QLabel {{
    font-weight: 500;
    color: {C.TEXT_SECONDARY};
    letter-spacing: 0.2px;
}}

/* ─── ToolTip ─────────────────────────────────────────────────── */
QToolTip {{
    background: {C.BG_CARD};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ─── DialogButtonBox ─────────────────────────────────────────── */
QDialogButtonBox QPushButton {{
    min-width: 90px;
    padding: 10px 22px;
}}
"""


# ══════════════════════════════════════════════════════════════════
#                    DIALOG STYLESHEET
# ══════════════════════════════════════════════════════════════════

DIALOG_STYLESHEET = f"""
QDialog {{
    background-color: {C.BG_DARK};
    color: {C.TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Inter', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}}
""" + GLOBAL_STYLESHEET


# ══════════════════════════════════════════════════════════════════
#                    HELPER BUILDERS
# ══════════════════════════════════════════════════════════════════

def styled_title(text: str, size: int = 18) -> str:
    """Return HTML-styled title string for QLabel."""
    return (
        f'<span style="font-size:{size}px; font-weight:700; '
        f'color:{C.TEXT_PRIMARY}; letter-spacing:0.8px;">{text}</span>'
    )


def styled_subtitle(text: str, size: int = 12) -> str:
    """Return HTML-styled subtitle string."""
    return (
        f'<span style="font-size:{size}px; color:{C.TEXT_SECONDARY}; '
        f'font-weight:400; letter-spacing:0.3px;">{text}</span>'
    )


def card_frame_style() -> str:
    """Return stylesheet for card-like QFrame/QWidget."""
    return f"""
        background: {C.BG_CARD};
        border: 1px solid {C.BORDER};
        border-radius: 12px;
        padding: 16px;
    """


def status_chip_style(status: str) -> str:
    """Return stylesheet for status chip labels (OK/DOWN/Unknown)."""
    if status == "OK":
        bg, fg = C.SUCCESS_BG, C.SUCCESS
    elif status == "DOWN":
        bg, fg = C.DANGER_BG, C.DANGER
    else:
        bg, fg = "rgba(85,85,85,0.15)", C.TEXT_DISABLED
    return f"""
        background: {bg};
        color: {fg};
        border-radius: 10px;
        padding: 3px 10px;
        font-weight: 600;
        font-size: 11px;
    """


# ══════════════════════════════════════════════════════════════════
#              COMPONENT-SPECIFIC STYLES
# ══════════════════════════════════════════════════════════════════

# ── Player Control Bar ────────────────────────────────────────────
PLAYER_BAR_STYLE = f"""
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(17,17,17,0.92), stop:1 rgba(11,11,11,0.98));
    border-top: 1px solid rgba(255,255,255,0.06);
    border-radius: 0;
"""

PLAYER_BUTTON_STYLE = f"""
    QToolButton {{
        width: 36px; height: 36px;
        border-radius: 18px;
        background: rgba(255,255,255,0.07);
        border: 1px solid rgba(255,255,255,0.08);
        color: {C.TEXT_PRIMARY};
    }}
    QToolButton:hover {{
        background: rgba(255,255,255,0.14);
        border: 1px solid rgba(255,255,255,0.2);
    }}
    QToolButton:pressed {{
        background: rgba(255,255,255,0.2);
    }}
"""

PLAYER_SLIDER_STYLE = f"""
    QSlider::groove:horizontal {{
        height: 3px;
        background: rgba(255,255,255,0.1);
        border-radius: 1px;
    }}
    QSlider::sub-page:horizontal {{
        background: {C.TEXT_PRIMARY};
        border-radius: 1px;
    }}
    QSlider::handle:horizontal {{
        background: #ffffff;
        border: none;
        border-radius: 7px;
        width: 14px;
        margin: -5px 0;
    }}
    QSlider::handle:horizontal:hover {{
        background: #ffffff;
        width: 16px;
        margin: -6px 0;
    }}
"""

BIG_PLAY_BUTTON_STYLE = f"""
    QToolButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(80,80,80,0.85), stop:1 rgba(50,50,50,0.85));
        border-radius: 48px;
        border: 3px solid rgba(255,255,255,0.7);
    }}
    QToolButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(120,120,120,0.9), stop:1 rgba(80,80,80,0.9));
        border: 3px solid rgba(255,255,255,0.95);
    }}
    QToolButton:pressed {{
        background: rgba(60,60,60,0.9);
    }}
"""

# ── Camera Tile ───────────────────────────────────────────────────
CAMERA_TILE_VIDEO_STYLE = f"""
    QLabel {{
        background-color: #000;
        border: 1px solid {C.BORDER};
        border-radius: 10px;
    }}
"""

CAMERA_TILE_TITLE_STYLE = f"""
    font-weight: 600;
    color: {C.TEXT_PRIMARY};
    font-size: 12px;
    padding: 3px 0;
    letter-spacing: 0.3px;
"""

# ── Login Dialog ──────────────────────────────────────────────────
LOGIN_STYLESHEET = f"""
    QDialog {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #0d0d0d, stop:0.5 #151515, stop:1 #1a1a1a);
        color: {C.TEXT_PRIMARY};
        font-family: 'Segoe UI', 'Inter', 'Helvetica Neue', sans-serif;
        font-size: 14px;
    }}
    QLineEdit {{
        border: 1px solid {C.BORDER};
        border-radius: 10px;
        padding: 13px 16px;
        background: {C.BG_INPUT};
        color: {C.TEXT_PRIMARY};
        font-size: 14px;
    }}
    QLineEdit:focus {{
        border: 1px solid {C.BORDER_FOCUS};
        background: {C.BG_CARD};
    }}
    QLineEdit::placeholder {{
        color: {C.TEXT_DISABLED};
    }}
    QPushButton#loginBtn {{
        background: {C.GRAD_PRIMARY};
        color: {C.TEXT_PRIMARY};
        border: 1px solid {C.BORDER_HOVER};
        border-radius: 10px;
        padding: 14px;
        font-size: 15px;
        font-weight: 700;
        letter-spacing: 0.8px;
    }}
    QPushButton#loginBtn:hover {{
        background-color: {C.BG_ELEVATED};
        border: 1px solid {C.BORDER_FOCUS};
    }}
    QPushButton#loginBtn:pressed {{
        background-color: {C.BG_INPUT};
    }}
    QCheckBox {{
        color: {C.TEXT_SECONDARY};
        font-size: 13px;
    }}
    QLabel#titleLabel {{
        font-size: 24px;
        font-weight: 700;
        color: {C.TEXT_PRIMARY};
        letter-spacing: 2px;
    }}
    QLabel#subtitleLabel {{
        font-size: 12px;
        color: {C.TEXT_SECONDARY};
        letter-spacing: 0.5px;
    }}
"""

# ── Admin Hub ─────────────────────────────────────────────────────
ADMIN_HUB_STYLESHEET = DIALOG_STYLESHEET + f"""
    QPushButton#adminCard {{
        background: {C.BG_CARD};
        border: 1px solid {C.BORDER};
        border-radius: 12px;
        padding: 0;
        text-align: left;
        min-height: 80px;
    }}
    QPushButton#adminCard:hover {{
        background: {C.BG_ELEVATED};
        border: 1px solid {C.BORDER_HOVER};
    }}
    QPushButton#adminCard:pressed {{
        background: {C.PRIMARY_BG};
        border: 1px solid {C.BORDER_FOCUS};
    }}
"""

# ── Splash ────────────────────────────────────────────────────────
SPLASH_BG_COLOR = C.BG_DARKEST
SPLASH_TITLE_COLOR = C.TEXT_PRIMARY
SPLASH_SUBTITLE_COLOR = C.TEXT_SECONDARY
SPLASH_MSG_COLOR = C.TEXT_DISABLED
