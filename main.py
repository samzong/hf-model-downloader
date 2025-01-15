"""
Main entry point for the Model Downloader application
"""

import sys
import os
import platform
import multiprocessing
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.ui import MainWindow

if __name__ == "__main__":
    # PyInstaller 打包环境的特殊处理
    if getattr(sys, 'frozen', False):
        # 运行在打包环境中
        os.environ['PYINSTALLER_HOOKS_DIR'] = '1'
        multiprocessing.freeze_support()
        # 设置多进程启动方法为 spawn
        if platform.system().lower() == 'darwin':  # 仅在 macOS 上设置
            multiprocessing.set_start_method('spawn')
    
    app = QApplication(sys.argv)
    
    # Set application icon based on platform
    system = platform.system().lower()
    if system == "darwin":
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.icns")
    elif system == "windows":
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
    else:
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
        
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 