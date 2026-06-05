"""
app_main.py — Application entry point with splash screen.
"""
from config import *
from theme import Colors, GLOBAL_STYLESHEET
from components import SplashScreen
from main_window import DeepBlueGridUltimate


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # ── App Icon ──────────────────────────────────────────────────
    if os.path.exists(LOGO_PATH):
        app.setWindowIcon(QIcon(LOGO_PATH))

    # ── Font ──────────────────────────────────────────────────────
    app.setFont(QFont("Segoe UI", 9))

    # ── Splash Screen ─────────────────────────────────────────────
    splash = SplashScreen()
    splash.show()
    QTimer.singleShot(2200, splash.close)

    # ── Main Window ───────────────────────────────────────────────
    window = DeepBlueGridUltimate()
    window.show()
    QTimer.singleShot(2400, lambda: splash.finish(window))

    sys.exit(app.exec_())


if __name__ == "__main__":
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)
        print(f"Created directory: {ASSETS_DIR}. Please add your 'logo.png' there.")

    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}")
        try:
            QMessageBox.critical(None, "Fatal Error", str(e))
        except Exception:
            pass