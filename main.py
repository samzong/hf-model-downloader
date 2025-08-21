"""
Main entry point for the Model Downloader application
"""

import multiprocessing
import os
import platform
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from src.resource_utils import get_asset_path
from src.ui import MainWindow

if __name__ == "__main__":
    try:
        if platform.system().lower() == "darwin":  # macOS
            multiprocessing.set_start_method("spawn", force=True)
        else:
            multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    if getattr(sys, "frozen", False):
        os.environ["PYINSTALLER_HOOKS_DIR"] = "1"
        multiprocessing.freeze_support()

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    app = QApplication(sys.argv)

    # Set application icon based on platform
    system = platform.system().lower()
    if system == "darwin":
        icon_path = get_asset_path("icon.icns")
    elif system == "windows":
        icon_path = get_asset_path("icon.ico")
    else:
        icon_path = get_asset_path("icon.png")

    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
