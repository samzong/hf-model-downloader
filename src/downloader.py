"""
Core downloader functionality
"""

import os
import json
import logging
import signal
from PyQt6.QtCore import QThread, pyqtSignal, QCoreApplication
from huggingface_hub import HfFolder, snapshot_download
from .utils import cleanup_lock_files, cleanup_environment

logger = logging.getLogger("huggingface_hub")

class LogHandler(logging.Handler):
    def __init__(self, log_signal):
        super().__init__()
        self.log_signal = log_signal

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)

class DownloadWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    status = pyqtSignal(str)
    log = pyqtSignal(str)
    
    def __init__(self, model_id, save_path, token=None, endpoint=None):
        super().__init__()
        self.model_id = model_id
        self.save_path = save_path
        self.token = token
        # 如果用户没有提供 endpoint，使用默认的 huggingface.co
        self.endpoint = endpoint if endpoint else "https://huggingface.co"
        self.is_cancelled = False
        
        # Setup logging handler
        self.log_handler = LogHandler(self.log)
        self.log_handler.setFormatter(
            logging.Formatter('%(message)s')
        )
        logger.addHandler(self.log_handler)

    def cancel_download(self):
        """优雅地取消下载"""
        self.is_cancelled = True
        self.log.emit("Cancelling download...")
        self.status.emit("Cancelling download...")
        self.cleanup()
        self.error.emit("Download cancelled by user")

    def cleanup(self):
        """Clean up resources and temporary files"""
        try:
            cleanup_environment()
            
            # Remove logging handler
            if self.log_handler in logger.handlers:
                logger.removeHandler(self.log_handler)
            
            # Clean up lock files while preserving downloaded chunks
            model_name = self.model_id.split('/')[-1]
            model_dir = os.path.join(self.save_path, model_name)
            cleanup_lock_files(model_dir)
            
            # 重置取消标志
            self.is_cancelled = False
            
        except Exception as e:
            self.log.emit(f"Warning: Cleanup error: {str(e)}")

    def run(self):
        try:
            # 禁用 Qt GUI 上下文
            os.environ["QT_QPA_PLATFORM"] = "minimal"
            
            # Create model directory
            model_name = self.model_id.split('/')[-1]
            model_dir = os.path.join(self.save_path, model_name)
            
            # Clean up any existing lock files
            cleanup_lock_files(model_dir)
            
            self.status.emit(f"Downloading model repository to {model_dir}...")
            self.log.emit(f"Starting download of {self.model_id} to {model_dir}")
            self.log.emit("Resume download is enabled - will reuse existing files if available")
            
            if self.is_cancelled:
                raise Exception("Download cancelled by user")

            if self.token:
                HfFolder.save_token(self.token)
                os.environ['HF_TOKEN'] = self.token
            
            if self.endpoint:
                os.environ['HF_ENDPOINT'] = self.endpoint
                os.environ['HF_HUB_DISABLE_SSL_VERIFICATION'] = '1'

            try:
                snapshot_download(
                    repo_id=self.model_id,
                    local_dir=model_dir,
                    use_auth_token=self.token,
                    local_dir_use_symlinks=False,
                    resume_download=True,
                    max_workers=8,
                    force_download=False,
                    ignore_patterns=["*.h5", "*.ot", "*.msgpack", ".*"]
                )
            except Exception as e:
                if "SSLError" in str(e):
                    self.log.emit("SSL Error detected. Trying to disable SSL verification...")
                    os.environ['HF_HUB_DISABLE_SSL_VERIFICATION'] = '1'
                    # 重试下载
                    snapshot_download(
                        repo_id=self.model_id,
                        local_dir=model_dir,
                        use_auth_token=self.token,
                        local_dir_use_symlinks=False,
                        resume_download=True,
                        max_workers=8,
                        force_download=False,
                        ignore_patterns=["*.h5", "*.ot", "*.msgpack", ".*"]
                    )
                else:
                    raise e

            if self.is_cancelled:
                raise Exception("Download cancelled by user")

            # Clean up lock files after successful download
            cleanup_lock_files(model_dir)
            
            self.log.emit(f"Model downloaded successfully to: {model_dir}")
            self.finished.emit()
            
        except Exception as e:
            error_msg = str(e)
            self.log.emit(f"Error: {error_msg}")
            
            if "Download cancelled by user" in error_msg:
                self.error.emit("Download cancelled by user")
                return
            
            # Try to clean up lock files on error
            try:
                cleanup_lock_files(model_dir)
            except:
                pass
            self.error.emit(error_msg)
        finally:
            self.cleanup()