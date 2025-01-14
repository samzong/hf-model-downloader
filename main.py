import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLineEdit, QPushButton, QLabel,
                           QFileDialog, QProgressBar, QMessageBox, QTextEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from huggingface_hub import HfFolder, snapshot_download, hf_hub_download
from huggingface_hub.utils import logging
import logging as python_logging
import json

# Configure logging to capture download progress
logger = python_logging.getLogger("huggingface_hub")
logger.setLevel(python_logging.INFO)

class LogHandler(python_logging.Handler):
    def __init__(self, progress_signal, log_signal):
        super().__init__()
        self.progress_signal = progress_signal
        self.log_signal = log_signal

    def emit(self, record):
        msg = self.format(record)
        if "Downloading" in msg and "%" in msg:
            try:
                # Extract percentage from download message
                percentage = float(msg.split("[")[1].split("%")[0])
                self.progress_signal.emit(percentage)
            except:
                pass
        self.log_signal.emit(msg)

class DownloadWorker(QThread):
    progress = pyqtSignal(float)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    status = pyqtSignal(str)
    log = pyqtSignal(str)
    
    def __init__(self, model_id, save_path, token=None, endpoint=None):
        super().__init__()
        self.model_id = model_id
        self.save_path = save_path
        self.token = token
        self.endpoint = endpoint
        self.is_cancelled = False
        
        # Setup logging handler
        self.log_handler = LogHandler(self.progress, self.log)
        self.log_handler.setFormatter(
            python_logging.Formatter('%(message)s')
        )
        logger.addHandler(self.log_handler)

    def cancel_download(self):
        self.is_cancelled = True
        self.log.emit("Cancelling download...")
        self.status.emit("Cancelling download...")
        # Force thread to stop
        self.terminate()
        self.wait()
        # Clean up
        self.cleanup()
        # Emit error signal to update UI
        self.error.emit("Download cancelled by user")

    def cleanup(self):
        """Clean up resources and temporary files"""
        try:
            # Clean up environment variables
            if self.endpoint and 'HF_ENDPOINT' in os.environ:
                del os.environ['HF_ENDPOINT']
            if self.token and 'HF_TOKEN' in os.environ:
                del os.environ['HF_TOKEN']
            if 'HF_HUB_DISABLE_SSL_VERIFICATION' in os.environ:
                del os.environ['HF_HUB_DISABLE_SSL_VERIFICATION']
            
            # Remove logging handler
            if self.log_handler in logger.handlers:
                logger.removeHandler(self.log_handler)
            
            # Clean up lock files while preserving downloaded chunks
            model_name = self.model_id.split('/')[-1]
            model_dir = os.path.join(self.save_path, model_name)
            self.cleanup_lock_files(model_dir)
        except Exception as e:
            self.log.emit(f"Warning: Cleanup error: {str(e)}")

    def cleanup_lock_files(self, directory):
        """Clean up any .lock files in the directory and its subdirectories."""
        self.log.emit("Cleaning up lock files (keeping downloaded chunks for resume)...")
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    # Only remove .lock files, keep .downloaded files and chunks
                    if file.endswith('.lock'):
                        lock_file = os.path.join(root, file)
                        try:
                            os.remove(lock_file)
                            self.log.emit(f"Removed lock file: {lock_file}")
                        except Exception as e:
                            self.log.emit(f"Warning: Could not remove lock file {lock_file}: {str(e)}")
        except Exception as e:
            self.log.emit(f"Warning: Error while cleaning lock files: {str(e)}")

    def run(self):
        try:
            # Set environment variables
            if self.token:
                HfFolder.save_token(self.token)
                os.environ['HF_TOKEN'] = self.token
            
            if self.endpoint:
                os.environ['HF_ENDPOINT'] = self.endpoint
                os.environ['HF_HUB_DISABLE_SSL_VERIFICATION'] = '1'
            
            # Create model directory
            model_name = self.model_id.split('/')[-1]
            model_dir = os.path.join(self.save_path, model_name)
            
            # Clean up any existing lock files
            self.cleanup_lock_files(model_dir)
            
            self.status.emit(f"Downloading model repository to {model_dir}...")
            self.log.emit(f"Starting download of {self.model_id} to {model_dir}")
            self.log.emit("Resume download is enabled - will reuse existing files if available")
            
            # First download the model info to get file list
            try:
                snapshot_info = hf_hub_download(
                    repo_id=self.model_id,
                    filename="model.safetensors.index.json",
                    use_auth_token=self.token,
                    local_dir=model_dir,
                    resume_download=True
                )
                with open(snapshot_info, 'r') as f:
                    model_files = json.load(f)
                    total_files = len(model_files['weight_map']) + 10  # Add some buffer for config files
            except:
                # If no index file, just proceed with snapshot download
                total_files = 1
            
            if self.is_cancelled:
                raise Exception("Download cancelled by user")
            
            # Download the model using snapshot_download
            local_dir = snapshot_download(
                repo_id=self.model_id,
                local_dir=model_dir,
                use_auth_token=self.token,
                local_dir_use_symlinks=False,
                resume_download=True,
                max_workers=8,
                force_download=False,
                ignore_patterns=["*.h5", "*.ot", "*.msgpack", ".*"]
            )
            
            if self.is_cancelled:
                raise Exception("Download cancelled by user")
            
            # Clean up lock files after successful download
            self.cleanup_lock_files(model_dir)
            
            self.log.emit(f"Model downloaded successfully to: {local_dir}")
            self.finished.emit()
            
        except Exception as e:
            error_msg = str(e)
            self.log.emit(f"Error: {error_msg}")
            
            if "Download cancelled by user" in error_msg:
                self.error.emit("Download cancelled by user")
                return
            
            # Handle SSL errors specifically
            if "SSLError" in error_msg:
                self.log.emit("SSL Error detected. Trying to disable SSL verification...")
                try:
                    os.environ['HF_HUB_DISABLE_SSL_VERIFICATION'] = '1'
                    # Retry download with SSL verification disabled
                    local_dir = snapshot_download(
                        repo_id=self.model_id,
                        local_dir=model_dir,
                        use_auth_token=self.token,
                        local_dir_use_symlinks=False,
                        resume_download=True,
                        max_workers=8,
                        force_download=False,
                        ignore_patterns=["*.h5", "*.ot", "*.msgpack", ".*"]
                    )
                    self.log.emit(f"Model downloaded successfully to: {local_dir}")
                    self.finished.emit()
                    return
                except Exception as e2:
                    error_msg = f"Failed even with SSL verification disabled: {str(e2)}"
            
            # Try to clean up lock files on error
            try:
                self.cleanup_lock_files(model_dir)
            except:
                pass
            self.error.emit(error_msg)
        finally:
            self.cleanup()

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
        
        # Model ID
        model_layout = QHBoxLayout()
        model_label = QLabel("Model ID:")
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("e.g., bert-base-uncased or username/model-name")
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
        self.endpoint_input.setPlaceholderText("https://huggingface.co")
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
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFormat("%.2f%%")
        layout.addWidget(self.progress_bar)
        
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
        endpoint = self.endpoint_input.text().strip() or None
        
        if not model_id:
            QMessageBox.warning(self, "Error", "Please enter a model ID")
            return
        
        if not save_path:
            QMessageBox.warning(self, "Error", "Please select a save path")
            return
        
        self.download_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Initializing download...")
        self.log_text.clear()
        
        self.download_worker = DownloadWorker(model_id, save_path, token, endpoint)
        self.download_worker.finished.connect(self.download_finished)
        self.download_worker.error.connect(self.download_error)
        self.download_worker.status.connect(self.update_status)
        self.download_worker.log.connect(self.update_log)
        self.download_worker.progress.connect(self.update_progress)
        self.download_worker.start()

    def stop_download(self):
        if self.download_worker and self.download_worker.isRunning():
            self.stop_button.setEnabled(False)
            self.status_label.setText("Stopping download...")
            self.download_worker.cancel_download()
            # Reset UI state
            self.download_button.setEnabled(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Download stopped")

    def update_status(self, message):
        self.status_label.setText(message)

    def update_progress(self, percentage):
        if not self.download_worker or not self.download_worker.is_cancelled:
            self.progress_bar.setValue(int(percentage))

    def update_log(self, message):
        self.log_text.append(message)
        # Scroll to the bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def download_finished(self):
        self.download_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Download completed!")
        self.log_text.append("✅ Download completed successfully!")
        QMessageBox.information(self, "Success", "Model downloaded successfully!")

    def download_error(self, error_msg):
        self.download_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if "cancelled by user" in error_msg.lower():
            self.status_label.setText("Download stopped")
            self.log_text.append("⏹️ Download stopped by user")
        else:
            self.status_label.setText("Download failed!")
            self.log_text.append(f"❌ Error: {error_msg}")
            QMessageBox.critical(self, "Error", f"Download failed: {error_msg}")
        self.progress_bar.setValue(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 