"""
User interface for the Model Downloader
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLineEdit, QPushButton, QLabel,
                           QFileDialog, QMessageBox, QTextEdit, QFrame)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from .downloader import DownloadWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hugging Face Model Downloader")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Help Section
        help_frame = QFrame()
        help_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        help_layout = QVBoxLayout(help_frame)
        
        help_title = QLabel("📖 Quick Guide")
        help_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        help_layout.addWidget(help_title)
        
        help_text = QLabel(
            "1. Find a model on Hugging Face Hub\n"
            "2. Copy the model ID (e.g., 'bert-base-uncased' or 'Qwen/Qwen2.5-Coder-1.5B-Instruct')\n"
            "3. Select a save location\n"
            "4. For private models, paste your access token\n"
            "5. Click Download to start\n"
            "6. Support resuming transmission from breakpoint"
        )
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text)
        
        # Quick Links
        links_layout = QHBoxLayout()
        browse_models_btn = QPushButton("🔍 Browse Models")
        browse_models_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://huggingface.co/models")))
        get_token_btn = QPushButton("🔑 Get Access Token")
        get_token_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://huggingface.co/settings/tokens")))
        
        links_layout.addWidget(browse_models_btn)
        links_layout.addWidget(get_token_btn)
        help_layout.addLayout(links_layout)
        
        layout.addWidget(help_frame)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Model ID
        model_layout = QHBoxLayout()
        model_label = QLabel("Model ID:")
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("e.g., bert-base-uncased or Qwen/Qwen2.5-Coder-1.5B-Instruct")
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_input)
        layout.addLayout(model_layout)
        
        # Save Path
        path_layout = QHBoxLayout()
        path_label = QLabel("Save Path:")
        self.path_input = QLineEdit()
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_path)
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_button)
        layout.addLayout(path_layout)
        
        # Token
        token_layout = QHBoxLayout()
        token_label = QLabel("Token:")
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Optional: For private models or higher rate limits")
        token_layout.addWidget(token_label)
        token_layout.addWidget(self.token_input)
        layout.addLayout(token_layout)
        
        # Endpoint
        endpoint_layout = QHBoxLayout()
        endpoint_label = QLabel("Endpoint:")
        self.endpoint_input = QLineEdit()
        self.endpoint_input.setText("https://hf-mirror.com")
        endpoint_layout.addWidget(endpoint_label)
        endpoint_layout.addWidget(self.endpoint_input)
        layout.addLayout(endpoint_layout)
        
        # Download and Stop Buttons
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.start_download)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_download)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)
        
        # Status Label
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        # Log Text Area
        log_label = QLabel("Download Log:")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        layout.addWidget(self.log_text)
        
        self.download_worker = None

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if path:
            self.path_input.setText(path)

    def start_download(self):
        model_id = self.model_input.text().strip()
        save_path = self.path_input.text().strip()
        token = self.token_input.text().strip() or None
        endpoint = self.endpoint_input.text().strip() or "https://huggingface.co"
        
        if not model_id:
            QMessageBox.warning(self, "Error", "Please enter a model ID")
            return
        
        if not save_path:
            QMessageBox.warning(self, "Error", "Please select a save path")
            return
        
        self.download_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.stop_button.setStyleSheet("QPushButton { background-color: #ff4444; color: white; }")
        self.status_label.setText("Initializing download...")
        self.log_text.clear()
        
        self.download_worker = DownloadWorker(model_id, save_path, token, endpoint)
        self.download_worker.finished.connect(self.download_finished)
        self.download_worker.error.connect(self.download_error)
        self.download_worker.status.connect(self.update_status)
        self.download_worker.log.connect(self.update_log)
        self.download_worker.start()

    def stop_download(self):
        if self.download_worker and self.download_worker.isRunning():
            self.stop_button.setEnabled(False)
            self.stop_button.setStyleSheet("")
            self.status_label.setText("Stopping download...")
            self.download_worker.cancel_download()
            self.download_button.setEnabled(True)
            self.status_label.setText("Download stopped")

    def update_status(self, message):
        self.status_label.setText(message)

    def update_log(self, message):
        self.log_text.append(message)
        # Scroll to the bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def download_finished(self):
        self.download_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("")
        self.status_label.setText("Download completed!")
        self.log_text.append("✅ Download completed successfully!")
        QMessageBox.information(self, "Success", "Model downloaded successfully!")

    def download_error(self, error_msg):
        self.download_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("")
        if "cancelled by user" in error_msg.lower():
            self.status_label.setText("Download stopped")
            self.log_text.append("⏹️ Download stopped by user")
        else:
            self.status_label.setText("Download failed!")
            self.log_text.append(f"❌ Error: {error_msg}")
            QMessageBox.critical(self, "Error", f"Download failed: {error_msg}") 