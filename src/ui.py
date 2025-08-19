"""
User interface for the Model Downloader
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLineEdit, QPushButton, QLabel,
                           QFileDialog, QMessageBox, QTextEdit, QFrame, QComboBox)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon
from .downloader import DownloadWorker
import platform
import os

# Repository information constants
GITHUB_REPO_URL = "https://github.com/samzong/hf-model-downloader"
AUTHOR_NAME = "samzong"
AUTHOR_GITHUB_URL = "https://github.com/samzong"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hugging Face Model Downloader")
        
        # Set window icon based on platform
        system = platform.system().lower()
        if system == "darwin":
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.icns")
        elif system == "windows":
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.ico")
        else:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.png")
            
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
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
            "1. Select download type (Model/Dataset)\n"
            "2. Find a model/dataset on Hugging Face Hub\n"
            "3. Copy the ID (e.g., 'bert-base-uncased' or 'squad' for datasets)\n"
            "4. Select a save location\n"
            "5. For private repositories, paste your access token\n"
            "6. Click Download to start\n"
            "7. Support resuming transmission from breakpoint"
        )
        help_text.setWordWrap(True)
        help_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        help_layout.addWidget(help_text)
        
        # Quick Links
        links_layout = QHBoxLayout()
        browse_models_btn = QPushButton("🔍 Browse Models")
        browse_models_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://huggingface.co/models")))
        browse_datasets_btn = QPushButton("📊 Browse Datasets")
        browse_datasets_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://huggingface.co/datasets")))
        get_token_btn = QPushButton("🔑 Get Access Token")
        get_token_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://huggingface.co/settings/tokens")))
        
        links_layout.addWidget(browse_models_btn)
        links_layout.addWidget(browse_datasets_btn)
        links_layout.addWidget(get_token_btn)
        help_layout.addLayout(links_layout)
        
        layout.addWidget(help_frame)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Download Type
        type_layout = QHBoxLayout()
        type_label = QLabel("Type:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Model", "Dataset"])
        self.type_combo.setCurrentText("Model")
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()  # Add stretch to keep combo box size reasonable
        layout.addLayout(type_layout)
        
        # Repository ID
        repo_layout = QHBoxLayout()
        self.repo_label = QLabel("Model ID:")
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("e.g., bert-base-uncased or Qwen/Qwen2.5-Coder-1.5B-Instruct")
        repo_layout.addWidget(self.repo_label)
        repo_layout.addWidget(self.repo_input)
        layout.addLayout(repo_layout)
        
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
        # 预填充镜像站点
        self.endpoint_input.setText("https://hf-mirror.com")
        self.endpoint_input.setPlaceholderText("default: https://hf-mirror.com")
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
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Log Text Area
        log_label = QLabel("Download Log:")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        layout.addWidget(self.log_text)
        
        # Footer Section
        footer_frame = QFrame()
        footer_layout = QHBoxLayout(footer_frame)
        
        # Add stretch to center content
        footer_layout.addStretch()
        
        # GitHub repository link
        github_btn = QPushButton("View on GitHub")
        github_btn.setFlat(True)  # Make it look like a label but clickable
        github_btn.setStyleSheet("QPushButton { font-size: 12px; color: #666; border: none; text-decoration: underline; }")
        github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_REPO_URL)))
        footer_layout.addWidget(github_btn)
        
        # Author information with clickable link
        author_btn = QPushButton(f"Created by {AUTHOR_NAME}")
        author_btn.setFlat(True)  # Make it look like a label but clickable
        author_btn.setStyleSheet("QPushButton { font-size: 12px; color: #666; border: none; text-decoration: underline; }")
        author_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(AUTHOR_GITHUB_URL)))
        footer_layout.addWidget(author_btn)
        
        # Add stretch to center content
        footer_layout.addStretch()
        
        layout.addWidget(footer_frame)
        
        self.download_worker = None

    def on_type_changed(self, type_text):
        """当下载类型改变时更新UI"""
        if type_text == "Dataset":
            self.repo_label.setText("Dataset ID:")
            self.repo_input.setPlaceholderText("e.g., squad, imdb, wikitext")
        else:
            self.repo_label.setText("Model ID:")
            self.repo_input.setPlaceholderText("e.g., bert-base-uncased or Qwen/Qwen2.5-Coder-1.5B-Instruct")

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if path:
            self.path_input.setText(path)

    def start_download(self):
        repo_id = self.repo_input.text().strip()
        save_path = self.path_input.text().strip()
        token = self.token_input.text().strip() or None
        repo_type = self.type_combo.currentText().lower()  # "model" or "dataset"
        
        # 获取 endpoint
        endpoint = self.endpoint_input.text().strip()
        # 如果用户完全清空了输入框，使用默认值
        if not endpoint:
            endpoint = "https://hf-mirror.com"
        
        if not repo_id:
            repo_type_text = "model ID" if repo_type == "model" else "dataset ID"
            self.update_status(f"Error: Please enter a {repo_type_text}", error=True)
            return
        
        if not save_path:
            self.update_status("Error: Please select a save path", error=True)
            return
        
        self.download_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.stop_button.setStyleSheet("QPushButton { background-color: #ff4444; color: white; }")
        self.update_status("Initializing download...")
        self.log_text.clear()
        
        self.download_worker = DownloadWorker(repo_id, save_path, token, endpoint, repo_type)
        self.download_worker.finished.connect(self.download_finished)
        self.download_worker.error.connect(self.download_error)
        self.download_worker.status.connect(self.update_status)
        self.download_worker.log.connect(self.update_log)
        self.download_worker.start()

    def stop_download(self):
        if self.download_worker and self.download_worker.isRunning():
            self.stop_button.setEnabled(False)
            self.stop_button.setStyleSheet("")
            self.update_status("Stopping download...")
            self.download_worker.cancel_download()
            self.download_button.setEnabled(True)

    def update_status(self, message, error=False):
        if error:
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
        else:
            self.status_label.setStyleSheet("font-weight: bold;")
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
        self.update_status("✅ Download completed successfully!")
        self.log_text.append("✅ Download completed successfully!")

    def download_error(self, error_msg):
        self.download_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("")
        if "cancelled by user" in error_msg.lower():
            self.update_status("⏹️ Download stopped by user")
            self.log_text.append("⏹️ Download stopped by user")
        else:
            self.update_status(f"❌ Error: {error_msg}", error=True)
            self.log_text.append(f"❌ Error: {error_msg}") 