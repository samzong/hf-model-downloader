import logging
import multiprocessing
import os
import platform
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from src.resource_utils import get_asset_path
from src.ui import MainWindow


def main():
    multiprocessing.freeze_support()
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app = QApplication(sys.argv)
    icon_name = {
        "darwin": "icon.icns",
        "windows": "icon.ico",
    }.get(platform.system().lower(), "icon.png")
    icon_path = get_asset_path(icon_name)
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
