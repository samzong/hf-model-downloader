"""
Main entry point for the Model Downloader application
"""

import sys
from PyQt6.QtWidgets import QApplication
from src.ui import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 