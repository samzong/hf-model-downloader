import os

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .resource_utils import get_asset_path
from .unified_downloader import UnifiedDownloadWorker

PLATFORM_LINKS = {
    0: {
        "platform": "huggingface",
        "endpoint": "https://hf-mirror.com",
        "models": "https://huggingface.co/models",
        "datasets": "https://huggingface.co/datasets",
        "token": "https://huggingface.co/settings/tokens",
    },
    1: {
        "platform": "modelscope",
        "endpoint": "https://modelscope.cn",
        "models": "https://modelscope.cn/models",
        "datasets": "https://modelscope.cn/datasets",
        "token": "https://modelscope.cn/my/myaccesstoken",
    },
}

GITHUB_REPO_URL = "https://github.com/samzong/hf-model-downloader"
AUTHOR_NAME = "samzong"
AUTHOR_GITHUB_URL = "https://github.com/samzong"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HF Model Downloader")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        standard_button_height = 32

        icon_layout = QHBoxLayout()
        icon_layout.setContentsMargins(10, 10, 10, 0)

        self.platform_button_group = QButtonGroup()
        self.platform_button_group.setExclusive(True)

        self.hf_button = QPushButton()
        hf_icon_path = get_asset_path("huggingface_logo.png")
        if os.path.exists(hf_icon_path):
            self.hf_button.setIcon(QIcon(hf_icon_path))
            self.hf_button.setIconSize(QSize(32, 32))
        self.hf_button.setCheckable(True)
        self.hf_button.setChecked(True)
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

        self.ms_button = QPushButton()
        ms_icon_path = get_asset_path("modelscope_logo.png")
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

        self.platform_button_group.idClicked.connect(self.on_platform_icon_changed)

        icon_layout.addWidget(self.hf_button)
        icon_layout.addWidget(self.ms_button)
        icon_layout.addStretch()

        layout.addLayout(icon_layout)

        help_frame = QFrame()
        help_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        help_layout = QVBoxLayout(help_frame)

        help_title = QLabel("📖 Quick Guide")
        help_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        help_layout.addWidget(help_title)

        guide_content_layout = QHBoxLayout()

        help_text = QLabel(
            "1. Select platform\n"
            "2. Enter model ID (e.g., 'bert-base-uncased')\n"
            "3. Choose save location\n"
            "4. Click Download (add token for private repos)\n"
        )
        help_text.setWordWrap(True)
        help_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        guide_content_layout.addWidget(help_text)

        links_layout = QVBoxLayout()
        links_layout.addStretch()
        self.browse_models_btn = QPushButton("🔍 Browse Models")
        self.browse_models_btn.setMaximumWidth(150)
        self.browse_models_btn.setFixedHeight(standard_button_height)
        self.browse_models_btn.clicked.connect(self.open_models_page)
        self.browse_datasets_btn = QPushButton("📊 Browse Datasets")
        self.browse_datasets_btn.setMaximumWidth(150)
        self.browse_datasets_btn.setFixedHeight(standard_button_height)
        self.browse_datasets_btn.clicked.connect(self.open_datasets_page)
        self.get_token_btn = QPushButton("🔑 Get Token")
        self.get_token_btn.setMaximumWidth(150)
        self.get_token_btn.setFixedHeight(standard_button_height)
        self.get_token_btn.clicked.connect(self.open_token_page)

        links_layout.addWidget(self.browse_models_btn)
        links_layout.addWidget(self.browse_datasets_btn)
        links_layout.addWidget(self.get_token_btn)
        links_layout.addStretch()

        guide_content_layout.addLayout(links_layout)
        help_layout.addLayout(guide_content_layout)

        layout.addWidget(help_frame)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        type_layout = QHBoxLayout()
        type_label = QLabel("Type:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Model", "Dataset"])
        self.type_combo.setCurrentText("Model")
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        repo_layout = QHBoxLayout()
        self.repo_label = QLabel("Model ID:")
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("e.g., qwen/Qwen2.5-Coder-1.5B-Instruct")
        repo_layout.addWidget(self.repo_label)
        repo_layout.addWidget(self.repo_input)
        layout.addLayout(repo_layout)

        path_layout = QHBoxLayout()
        path_label = QLabel("Save Path:")
        self.path_input = QLineEdit()
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_path)
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_button)
        layout.addLayout(path_layout)

        token_layout = QHBoxLayout()
        token_label = QLabel("Token:")
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText(
            "Optional: For private models or higher rate limits"
        )
        token_layout.addWidget(token_label)
        token_layout.addWidget(self.token_input)
        layout.addLayout(token_layout)

        endpoint_layout = QHBoxLayout()
        endpoint_label = QLabel("Endpoint:")
        self.endpoint_input = QLineEdit()
        self.endpoint_input.setText("https://hf-mirror.com")
        self.endpoint_input.setPlaceholderText("default: https://hf-mirror.com")
        endpoint_layout.addWidget(endpoint_label)
        endpoint_layout.addWidget(self.endpoint_input)
        layout.addLayout(endpoint_layout)

        button_layout = QHBoxLayout()
        self.download_button = QPushButton("Download")
        self.download_button.setFixedHeight(standard_button_height)
        self.download_button.clicked.connect(self.start_download)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setFixedHeight(standard_button_height)
        self.stop_button.clicked.connect(self.stop_download)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(100)
        layout.addWidget(self.log_text)

        footer_frame = QFrame()
        footer_layout = QHBoxLayout(footer_frame)

        footer_layout.addStretch()

        github_btn = QPushButton("View on GitHub")
        github_btn.setFlat(True)
        github_btn.setStyleSheet(
            "QPushButton { "
            "font-size: 12px; color: #666; border: none; text-decoration: underline; "
            "}"
        )
        github_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(GITHUB_REPO_URL))
        )
        footer_layout.addWidget(github_btn)

        author_btn = QPushButton(f"Created by {AUTHOR_NAME}")
        author_btn.setFlat(True)
        author_btn.setStyleSheet(
            "QPushButton { "
            "font-size: 12px; color: #666; border: none; text-decoration: underline; "
            "}"
        )
        author_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(AUTHOR_GITHUB_URL))
        )
        footer_layout.addWidget(author_btn)

        footer_layout.addStretch()

        layout.addWidget(footer_frame)

        self.setMinimumSize(800, 660)

        self.download_worker = None
        self._closing = False

    def closeEvent(self, event):
        if self.download_worker is not None:
            self._closing = True
            self.stop_download()
            event.ignore()
            return
        event.accept()

    def platform_config(self):
        return PLATFORM_LINKS[self.platform_button_group.checkedId()]

    def on_platform_icon_changed(self, button_id):
        self.endpoint_input.setText(PLATFORM_LINKS[button_id]["endpoint"])

    def open_models_page(self):
        QDesktopServices.openUrl(QUrl(self.platform_config()["models"]))

    def open_datasets_page(self):
        QDesktopServices.openUrl(QUrl(self.platform_config()["datasets"]))

    def open_token_page(self):
        QDesktopServices.openUrl(QUrl(self.platform_config()["token"]))

    def on_type_changed(self, type_text):
        if type_text == "Dataset":
            self.repo_label.setText("Dataset ID:")
            self.repo_input.setPlaceholderText("e.g., baicai003/Llama3-Chinese-dataset")
        else:
            self.repo_label.setText("Model ID:")
            self.repo_input.setPlaceholderText("e.g., deepseek-ai/DeepSeek-R1")

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if path:
            self.path_input.setText(path)

    def start_download(self):
        if self.download_worker is not None:
            return
        repo_id = self.repo_input.text().strip()
        save_path = self.path_input.text().strip()
        token = self.token_input.text().strip() or None
        repo_type = self.type_combo.currentText().lower()
        config = self.platform_config()

        endpoint = self.endpoint_input.text().strip() or config["endpoint"]

        if not repo_id:
            repo_type_text = "model ID" if repo_type == "model" else "dataset ID"
            self.update_status(f"Error: Please enter a {repo_type_text}", error=True)
            return

        if not save_path:
            self.update_status("Error: Please select a save path", error=True)
            return

        self.download_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.stop_button.setStyleSheet(
            "QPushButton { background-color: #ff4444; color: white; }"
        )
        self.update_status("Initializing download...")
        self.log_text.clear()

        self.download_worker = UnifiedDownloadWorker(
            config["platform"], repo_id, save_path, token, endpoint, repo_type
        )
        self.download_worker.succeeded.connect(
            self.download_finished, Qt.ConnectionType.QueuedConnection
        )
        self.download_worker.stopped.connect(
            self.download_stopped, Qt.ConnectionType.QueuedConnection
        )
        self.download_worker.error.connect(
            self.download_error, Qt.ConnectionType.QueuedConnection
        )
        self.download_worker.status.connect(
            self.update_status, Qt.ConnectionType.QueuedConnection
        )
        self.download_worker.log.connect(
            self.update_log, Qt.ConnectionType.QueuedConnection
        )

        self.download_worker.finished.connect(
            self._on_worker_finished, Qt.ConnectionType.QueuedConnection
        )
        self.download_worker.start()

    def stop_download(self):
        if self.download_worker and self.download_worker.isRunning():
            self.stop_button.setEnabled(False)
            self.stop_button.setStyleSheet("")
            self.update_status("Stopping download...")
            self.download_worker.cancel_download()

    def update_status(self, message, error=False):
        if error:
            self.log_text.append(f"❌ {message}")
        else:
            self.log_text.append(f"ℹ️ {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def update_log(self, message):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def download_finished(self):
        self.update_log("✅ Download completed successfully!")

    def download_stopped(self):
        self.update_log("⏹️ Download stopped by user")

    def download_error(self, error_msg):
        self.update_status(f"Error: {error_msg}", error=True)

    def _on_worker_finished(self):
        worker = self.download_worker
        worker.wait()
        self.download_worker = None
        worker.deleteLater()
        self.download_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("")
        if self._closing:
            self.close()
