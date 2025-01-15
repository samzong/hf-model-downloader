"""
Main entry point for the Model Downloader application
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.ui import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application icon
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 