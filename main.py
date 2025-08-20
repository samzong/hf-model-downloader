"""
Main entry point for the Model Downloader application
"""

import multiprocessing
import os
import platform
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from src.ui import MainWindow
from src.resource_utils import get_asset_path

if __name__ == "__main__":
    # 设置多进程方法 - 必须在创建 QApplication 之前设置
    try:
        if platform.system().lower() == "darwin":  # macOS
            multiprocessing.set_start_method("spawn", force=True)
        else:
            multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        # 如果已经设置过，忽略错误
        pass

    # PyInstaller 打包环境的特殊处理
    if getattr(sys, "frozen", False):
        # 运行在打包环境中
        os.environ["PYINSTALLER_HOOKS_DIR"] = "1"
        multiprocessing.freeze_support()

    # 添加环境变量以避免 Qt 相关的段错误
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
