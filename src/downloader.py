"""
Core downloader functionality
"""

import os
import json
import logging
import signal
import multiprocessing
from PyQt6.QtCore import QThread, pyqtSignal
from huggingface_hub import HfFolder, snapshot_download, hf_hub_download
from .utils import cleanup_lock_files, cleanup_environment

logger = logging.getLogger("huggingface_hub")

class LogHandler(logging.Handler):
    def __init__(self, log_signal):
        super().__init__()
        self.log_signal = log_signal

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)

def download_process(repo_id, local_dir, token, endpoint, ignore_patterns):
    """Separate process for downloading"""
    try:
        if token:
            HfFolder.save_token(token)
            os.environ['HF_TOKEN'] = token
        
        if endpoint:
            os.environ['HF_ENDPOINT'] = endpoint
            os.environ['HF_HUB_DISABLE_SSL_VERIFICATION'] = '1'

        return snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            use_auth_token=token,
            local_dir_use_symlinks=False,
            resume_download=True,
            max_workers=8,
            force_download=False,
            ignore_patterns=ignore_patterns
        )
    except Exception as e:
        return str(e)

class DownloadWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    status = pyqtSignal(str)
    log = pyqtSignal(str)
    
    def __init__(self, model_id, save_path, token=None, endpoint="https://hf-mirror.com"):
        super().__init__()
        self.model_id = model_id
        self.save_path = save_path
        self.token = token
        self.endpoint = endpoint
        self.is_cancelled = False
        self.process = None
        
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
        
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=1)
            if self.process.is_alive():
                self.process.kill()
                self.process.join()
        
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

            # 创建下载进程
            ctx = multiprocessing.get_context('spawn')
            self.process = ctx.Process(
                target=download_process,
                args=(
                    self.model_id,
                    model_dir,
                    self.token,
                    self.endpoint,
                    ["*.h5", "*.ot", "*.msgpack", ".*"]
                )
            )
            self.process.start()
            self.process.join()

            if self.is_cancelled:
                raise Exception("Download cancelled by user")
            
            if self.process.exitcode != 0:
                raise Exception("Download process failed")

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
            
            # Handle SSL errors specifically
            if "SSLError" in error_msg:
                self.log.emit("SSL Error detected. Trying to disable SSL verification...")
                try:
                    os.environ['HF_HUB_DISABLE_SSL_VERIFICATION'] = '1'
                    # 重试下载
                    ctx = multiprocessing.get_context('spawn')
                    self.process = ctx.Process(
                        target=download_process,
                        args=(
                            self.model_id,
                            model_dir,
                            self.token,
                            self.endpoint,
                            ["*.h5", "*.ot", "*.msgpack", ".*"]
                        )
                    )
                    self.process.start()
                    self.process.join()

                    if self.process.exitcode == 0:
                        self.log.emit(f"Model downloaded successfully to: {model_dir}")
                        self.finished.emit()
                        return
                    else:
                        error_msg = "Failed even with SSL verification disabled"
                except Exception as e2:
                    error_msg = f"Failed even with SSL verification disabled: {str(e2)}"
            
            # Try to clean up lock files on error
            try:
                cleanup_lock_files(model_dir)
            except:
                pass
            self.error.emit(error_msg)
        finally:
            self.cleanup() 