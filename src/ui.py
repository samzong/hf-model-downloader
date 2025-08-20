"""
User interface for the Model Downloader
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLineEdit, QPushButton, QLabel,
                           QFileDialog, QMessageBox, QTextEdit, QFrame, QComboBox, QButtonGroup)
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtGui import QDesktopServices, QIcon
from .unified_downloader import UnifiedDownloadWorker
import platform
import os

# Repository information constants
GITHUB_REPO_URL = "https://github.com/samzong/hf-model-downloader"
AUTHOR_NAME = "samzong"
AUTHOR_GITHUB_URL = "https://github.com/samzong"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hugging Face & ModelScope Model Downloader")
        
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
        
        # Platform Selection Icons at the top
        icon_layout = QHBoxLayout()
        icon_layout.setContentsMargins(10, 10, 10, 0)
        
        # Create button group for exclusive selection
        self.platform_button_group = QButtonGroup()
        self.platform_button_group.setExclusive(True)
        
        # Hugging Face icon button
        self.hf_button = QPushButton()
        hf_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "huggingface_logo.png")
        if os.path.exists(hf_icon_path):
            self.hf_button.setIcon(QIcon(hf_icon_path))
            self.hf_button.setIconSize(QSize(32, 32))
        self.hf_button.setCheckable(True)
        self.hf_button.setChecked(True)  # Default to Hugging Face
        self.hf_button.setStyleSheet("""
            QPushButton {
                border: 2px solid #ddd;
                border-radius: 6px;
                padding: 8px;
                background-color: white;
            }
            QPushButton:hover {
                border-color: #FFD21E;
                background-color: #fffbf0;
            }
            QPushButton:checked {
                border-color: #FFD21E;
                background-color: #fff8e1;
            }
        """)
        self.platform_button_group.addButton(self.hf_button, 0)
        
        # ModelScope icon button  
        self.ms_button = QPushButton()
        ms_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "modelscope_logo.png")
        if os.path.exists(ms_icon_path):
            self.ms_button.setIcon(QIcon(ms_icon_path))
            self.ms_button.setIconSize(QSize(32, 32))
        self.ms_button.setCheckable(True)
        self.ms_button.setStyleSheet("""
            QPushButton {
                border: 2px solid #ddd;
                border-radius: 6px;
                padding: 8px;
                background-color: white;
            }
            QPushButton:hover {
                border-color: #1677FF;
                background-color: #f0f8ff;
            }
            QPushButton:checked {
                border-color: #1677FF;
                background-color: #e6f3ff;
            }
        """)
        self.platform_button_group.addButton(self.ms_button, 1)
        
        # Connect button group to platform change handler
        self.platform_button_group.idClicked.connect(self.on_platform_icon_changed)
        
        # Add buttons to layout (left-aligned)
        icon_layout.addWidget(self.hf_button)
        icon_layout.addWidget(self.ms_button)
        icon_layout.addStretch()  # Push icons to the left
        
        layout.addLayout(icon_layout)
        
        # Help Section
        help_frame = QFrame()
        help_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        help_layout = QVBoxLayout(help_frame)
        
        help_title = QLabel("📖 Quick Guide")
        help_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        help_layout.addWidget(help_title)
        
        help_text = QLabel(
            "1. Select platform (Hugging Face or ModelScope)\n"
            "2. Select download type (Model/Dataset)\n"
            "3. Find a model/dataset on the selected hub\n"
            "4. Copy the ID (e.g., 'bert-base-uncased' or 'qwen/Qwen2.5-Coder-1.5B-Instruct')\n"
            "5. Select a save location\n"
            "6. For private repositories, paste your access token\n"
            "7. Click Download to start\n"
            "8. Support resuming transmission from breakpoint"
        )
        help_text.setWordWrap(True)
        help_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        help_layout.addWidget(help_text)
        
        # Quick Links
        links_layout = QHBoxLayout()
        self.browse_models_btn = QPushButton("🔍 Browse HF Models")
        self.browse_models_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://huggingface.co/models")))
        self.browse_datasets_btn = QPushButton("📊 Browse HF Datasets")
        self.browse_datasets_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://huggingface.co/datasets")))
        self.get_token_btn = QPushButton("🔑 Get HF Token")
        self.get_token_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://huggingface.co/settings/tokens")))
        
        links_layout.addWidget(self.browse_models_btn)
        links_layout.addWidget(self.browse_datasets_btn)
        links_layout.addWidget(self.get_token_btn)
        help_layout.addLayout(links_layout)
        
        layout.addWidget(help_frame)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Hidden Platform Selection (keep for compatibility)
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["Hugging Face", "ModelScope"])
        self.platform_combo.setCurrentText("Hugging Face")
        self.platform_combo.currentTextChanged.connect(self.on_platform_changed)
        self.platform_combo.hide()  # Hide the combo box since we're using icons
        
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

    def closeEvent(self, event):
        """Handle window close event - ensure worker is cleaned up"""
        if self.download_worker and self.download_worker.isRunning():
            # Disconnect all signals first to prevent crashes during cleanup
            self.download_worker.finished.disconnect()
            self.download_worker.error.disconnect()
            self.download_worker.status.disconnect()
            self.download_worker.log.disconnect()
            
            # Cancel the download and wait for completion
            self.download_worker.cancel_download()
            # Use a timeout to avoid indefinite blocking
            if not self.download_worker.wait(5000):  # Wait max 5 seconds
                # Force terminate if it doesn't finish gracefully
                self.download_worker.terminate()
                self.download_worker.wait()
        event.accept()

    def on_platform_icon_changed(self, button_id):
        """Handle platform icon button changes"""
        if button_id == 0:  # Hugging Face
            platform_text = "Hugging Face"
        else:  # ModelScope
            platform_text = "ModelScope"
        
        # Update the hidden combo box to keep everything in sync
        self.platform_combo.setCurrentText(platform_text)

    def on_platform_changed(self, platform_text):
        """当平台改变时更新UI"""
        if platform_text == "ModelScope":
            # 更新按钮和链接
            self.browse_models_btn.setText("🔍 Browse MS Models")
            self.browse_models_btn.clicked.disconnect()
            self.browse_models_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://modelscope.cn/models")))
            
            self.browse_datasets_btn.setText("📊 Browse MS Datasets")
            self.browse_datasets_btn.clicked.disconnect()
            self.browse_datasets_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://modelscope.cn/datasets")))
            
            self.get_token_btn.setText("🔑 Get MS Token")
            self.get_token_btn.clicked.disconnect()
            self.get_token_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://modelscope.cn/my/myaccesstoken")))
            
            # 更新endpoint
            self.endpoint_input.setText("https://modelscope.cn")
            self.endpoint_input.setPlaceholderText("default: https://modelscope.cn")
            
            # 更新模型ID示例
            if self.type_combo.currentText() == "Dataset":
                self.repo_input.setPlaceholderText("e.g., modelscope/chinese-text-classification-dataset")
            else:
                self.repo_input.setPlaceholderText("e.g., qwen/Qwen2.5-Coder-1.5B-Instruct, damo/nlp_bert_base-chinese")
        else:
            # Hugging Face
            self.browse_models_btn.setText("🔍 Browse HF Models")
            self.browse_models_btn.clicked.disconnect()
            self.browse_models_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://huggingface.co/models")))
            
            self.browse_datasets_btn.setText("📊 Browse HF Datasets")
            self.browse_datasets_btn.clicked.disconnect()
            self.browse_datasets_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://huggingface.co/datasets")))
            
            self.get_token_btn.setText("🔑 Get HF Token")
            self.get_token_btn.clicked.disconnect()
            self.get_token_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://huggingface.co/settings/tokens")))
            
            # 更新endpoint
            self.endpoint_input.setText("https://hf-mirror.com")
            self.endpoint_input.setPlaceholderText("default: https://hf-mirror.com")
            
            # 更新模型ID示例
            if self.type_combo.currentText() == "Dataset":
                self.repo_input.setPlaceholderText("e.g., squad, imdb, wikitext")
            else:
                self.repo_input.setPlaceholderText("e.g., bert-base-uncased or Qwen/Qwen2.5-Coder-1.5B-Instruct")

    def on_type_changed(self, type_text):
        """当下载类型改变时更新UI"""
        platform = self.platform_combo.currentText()
        if type_text == "Dataset":
            self.repo_label.setText("Dataset ID:")
            if platform == "ModelScope":
                self.repo_input.setPlaceholderText("e.g., modelscope/chinese-text-classification-dataset")
            else:
                self.repo_input.setPlaceholderText("e.g., squad, imdb, wikitext")
        else:
            self.repo_label.setText("Model ID:")
            if platform == "ModelScope":
                self.repo_input.setPlaceholderText("e.g., qwen/Qwen2.5-Coder-1.5B-Instruct, damo/nlp_bert_base-chinese")
            else:
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
        platform = self.platform_combo.currentText()  # "Hugging Face" or "ModelScope"
        
        # 获取 endpoint
        endpoint = self.endpoint_input.text().strip()
        # 如果用户完全清空了输入框，使用默认值
        if not endpoint:
            if platform == "ModelScope":
                endpoint = "https://modelscope.cn"
            else:
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
        
        # 根据平台选择相应的下载器
        if platform == "ModelScope":
            self.download_worker = UnifiedDownloadWorker('modelscope', repo_id, save_path, token, endpoint, repo_type)
        else:
            self.download_worker = UnifiedDownloadWorker('huggingface', repo_id, save_path, token, endpoint, repo_type)
            
        # Use Qt.QueuedConnection to ensure thread-safe signal emission
        self.download_worker.finished.connect(self.download_finished, Qt.ConnectionType.QueuedConnection)
        self.download_worker.error.connect(self.download_error, Qt.ConnectionType.QueuedConnection)
        self.download_worker.status.connect(self.update_status, Qt.ConnectionType.QueuedConnection)
        self.download_worker.log.connect(self.update_log, Qt.ConnectionType.QueuedConnection)
        
        # Also connect to the worker's finished signal to handle cleanup
        self.download_worker.finished.connect(self._on_worker_finished, Qt.ConnectionType.QueuedConnection)
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
    
    def _on_worker_finished(self):
        """Handle worker cleanup when download completes or fails"""
        if hasattr(self, 'download_worker') and self.download_worker:
            # Wait for thread to fully stop before cleanup
            if self.download_worker.isRunning():
                self.download_worker.wait(3000)  # Wait up to 3 seconds
            
            # Clear the worker reference
            self.download_worker = None 