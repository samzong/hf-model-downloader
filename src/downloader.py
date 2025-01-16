"""
Core downloader functionality
"""

import os
import json
import logging
import signal
import threading
import sys
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional, Callable
import threading
import multiprocessing
from PyQt6.QtCore import QObject, pyqtSignal
from huggingface_hub import HfFolder, snapshot_download, HfApi
from huggingface_hub.constants import HF_HUB_ENABLE_HF_TRANSFER
from .utils import cleanup_lock_files, cleanup_environment
from tqdm.auto import tqdm

# 配置日志
logger = logging.getLogger("huggingface_hub")
qt_logger = logging.getLogger("PyQt6")
qt_logger.setLevel(logging.DEBUG)

class DownloadProgressBar(tqdm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current = self.n

    def update(self, n):
        super().update(n)
        self._current += n

def download_model(model_id: str, save_path: str, token: str = None, endpoint: str = None, pipe=None):
    """独立的下载函数，可以被多进程调用"""
    try:
        print("\n=== Download Process Debug Info ===")
        print("Process ID:", os.getpid())
        print("Parent Process ID:", os.getppid())
        print("Current Working Directory:", os.getcwd())
        print("Python Executable:", sys.executable)
        print("\nEnvironment Variables:")
        qt_vars = {k: v for k, v in os.environ.items() if 'QT' in k.upper()}
        print("Qt-related env vars:", qt_vars)
        print("\nPython Path:")
        for p in sys.path:
            print(f"  - {p}")
        print("\nLoaded Qt-related modules:")
        qt_modules = {k: v for k, v in sys.modules.items() if 'qt' in k.lower()}
        print(qt_modules)
        print("\nProcess Start Method:", multiprocessing.get_start_method())
        print("=== End Debug Info ===\n")

        # 重定向标准输出和标准错误
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        if pipe:
            sys.stdout = pipe
            sys.stderr = pipe
        
        # 设置环境变量
        if token:
            HfFolder.save_token(token)
            os.environ['HF_TOKEN'] = token
        
        # 设置 endpoint 和相关环境变量
        if endpoint:
            os.environ['HF_ENDPOINT'] = endpoint
            # 只有使用镜像站时才禁用 SSL 验证
            if "hf-mirror.com" in endpoint:
                os.environ['HF_HUB_DISABLE_SSL_VERIFICATION'] = '1'
            else:
                os.environ.pop('HF_HUB_DISABLE_SSL_VERIFICATION', None)
        else:
            os.environ.pop('HF_HUB_DISABLE_SSL_VERIFICATION', None)
        
        # 禁用 HF Transfer，使用标准 HTTPS 下载
        os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '0'
        # 设置较大的连接超时
        os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '300'
        # 启用并发下载
        os.environ['HF_HUB_ENABLE_CONCURRENT_DOWNLOAD'] = '1'
        
        # 执行下载
        model_dir = os.path.join(save_path, model_id.split('/')[-1])
        
        # 设置信号处理，确保可以正确响应终止信号
        def signal_handler(signum, frame):
            if pipe:
                pipe.send("Download interrupted by signal")
            sys.exit(1)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            # 获取CPU核心数，但最多使用16个线程
            max_workers = min(multiprocessing.cpu_count() * 2, 16)
            
            result = snapshot_download(
                repo_id=model_id,
                local_dir=model_dir,
                token=token,
                force_download=False,
                max_workers=max_workers,
                tqdm_class=DownloadProgressBar,
                ignore_patterns=["*.h5", "*.ot", "*.msgpack", "*.bin", "*.pkl", "*.onnx", ".*"],
                local_files_only=False,
                etag_timeout=30,
                proxies=None,  # 不使用代理
                endpoint=endpoint
            )
            return True
        except KeyboardInterrupt:
            if pipe:
                pipe.send("Download cancelled by user")
            return False
        
    except Exception as e:
        error_msg = str(e)
        if pipe:
            pipe.send(f"Error during download: {error_msg}")
        return False
    finally:
        # 恢复标准输出和标准错误
        if pipe:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            try:
                pipe.send("DOWNLOAD_COMPLETE")
            except:
                pass

class LogHandler(logging.Handler):
    def __init__(self, log_signal):
        super().__init__()
        self.log_signal = log_signal

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)

class PipeWriter:
    def __init__(self, pipe):
        self.pipe = pipe
        self.buffer = ""
        self.last_progress = ""
    
    def write(self, text):
        # 处理所有输出，包括进度条
        if '\r' in text:  # 进度条更新
            # 清除旧的进度信息
            self.buffer = text.split('\r')[-1]
            if self.buffer.strip() and self.buffer != self.last_progress:
                self.pipe.send(self.buffer)
                self.last_progress = self.buffer
        elif '\n' in text:  # 普通日志输出
            self.buffer += text
            lines = self.buffer.split('\n')
            self.buffer = lines[-1]  # 保留最后一个不完整的行
            for line in lines[:-1]:
                if line.strip() and line != self.last_progress:  # 避免重复发送相同的进度信息
                    self.pipe.send(line)
        else:
            self.buffer += text
    
    def flush(self):
        if self.buffer.strip() and self.buffer != self.last_progress:
            self.pipe.send(self.buffer)
            self.buffer = ""

class DownloadWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    status = pyqtSignal(str)
    log = pyqtSignal(str)
    
    def __init__(self, model_id, save_path, token=None, endpoint=None):
        super().__init__()
        self.model_id = model_id
        self.save_path = save_path
        self.token = token
        self.endpoint = endpoint if endpoint else "https://huggingface.co"
        
        # 设置日志
        self._logger = logging.getLogger("DownloadWorker")
        self._logger.setLevel(logging.DEBUG)
        
        # 设置日志处理器
        self.log_handler = LogHandler(self.log)
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(self.log_handler)
        self._logger.addHandler(self.log_handler)
        qt_logger.addHandler(self.log_handler)

        # 保存模型目录路径
        self.model_name = self.model_id.split('/')[-1]
        self.model_dir = os.path.join(self.save_path, self.model_name)
        self._logger.debug(f"Initialized worker for model {model_id} with save path {save_path}")
        
        # 添加取消事件和进程引用
        self._cancel_event = threading.Event()
        self._download_process = None
        self._pipe_reader = None
        self._pipe_writer = None
        self._output_thread = None
        self._worker_thread = None
        self._is_running = False

    def isRunning(self):
        """检查下载是否正在运行"""
        return self._is_running and self._worker_thread and self._worker_thread.is_alive()

    def start(self):
        """启动下载任务"""
        if not self.isRunning():
            self._is_running = True
            self._cancel_event.clear()
            self._worker_thread = threading.Thread(target=self._run)
            self._worker_thread.daemon = True
            self._worker_thread.start()

    def cancel_download(self):
        """取消下载"""
        if not self.isRunning():
            return

        self._logger.debug("Cancel download requested")
        self.log.emit("Cancelling download...")
        self.status.emit("Cancelling download...")
        
        # 设置取消事件
        self._cancel_event.set()
        
        # 尝试正常终止进程
        if self._download_process and self._download_process.is_alive():
            try:
                # 首先尝试正常终止
                self._download_process.terminate()
                # 等待一段时间让进程正常退出
                for _ in range(30):  # 最多等待3秒
                    if not self._download_process.is_alive():
                        break
                    time.sleep(0.1)
                
                # 如果进程还在运行，强制终止
                if self._download_process.is_alive():
                    self._logger.warning("Process not responding to terminate, forcing kill")
                    import psutil
                    try:
                        parent = psutil.Process(self._download_process.pid)
                        for child in parent.children(recursive=True):
                            try:
                                child.kill()  # 使用 kill 而不是 terminate
                            except psutil.NoSuchProcess:
                                pass
                        parent.kill()  # 使用 kill 而不是 terminate
                    except psutil.NoSuchProcess:
                        pass
                    except Exception as e:
                        self._logger.error(f"Error killing process: {e}")
                
                self._logger.debug("Download process terminated")
            except Exception as e:
                self._logger.error(f"Error terminating download process: {e}")
        
        # 清理环境和文件，但保持 endpoint 设置
        self.cleanup()
        self._is_running = False
        self.error.emit("Download cancelled by user")
        self._logger.debug("Download cancellation complete")

    def _run(self):
        """在独立线程中运行下载任务"""
        try:
            self._logger.debug("Starting download worker run")
            # 清理现有的锁文件
            cleanup_lock_files(self.model_dir)
            
            self.status.emit(f"Downloading model repository to {self.model_dir}...")
            self.log.emit(f"Starting download of {self.model_id} to {self.model_dir}")

            # 创建管道和输出处理线程
            self._pipe_reader, self._pipe_writer = multiprocessing.Pipe(duplex=False)
            pipe_writer = PipeWriter(self._pipe_writer)
            
            # 启动输出处理线程
            self._output_thread = threading.Thread(target=self._process_pipe_output)
            self._output_thread.daemon = True
            self._output_thread.start()

            # 在新进程中启动下载任务
            self._download_process = multiprocessing.get_context('spawn').Process(
                target=download_model,
                args=(self.model_id, self.save_path, self.token, self.endpoint, pipe_writer)
            )
            self._download_process.start()
            
            # 等待下载完成或取消
            download_completed = False
            while self._download_process.is_alive():
                if self._cancel_event.is_set():
                    self._logger.debug("Cancel event detected, terminating process")
                    self._download_process.terminate()
                    break
                self._download_process.join(timeout=0.1)
            
            # 检查下载是否成功完成
            if self._download_process.exitcode == 0:
                download_completed = True
            
            # 停止输出处理线程
            self._cancel_event.set()
            if self._output_thread:
                self._output_thread.join()
            
            # 处理下载结果
            if download_completed:
                cleanup_lock_files(self.model_dir)
                self.log.emit(f"Model downloaded successfully to: {self.model_dir}")
                self._logger.debug("Download completed successfully")
                self.finished.emit()
            elif self._cancel_event.is_set() and not download_completed:
                raise Exception("Download cancelled by user")
            else:
                raise Exception("Download process failed")
            
        except Exception as e:
            error_msg = str(e)
            self._logger.error(f"Download failed: {error_msg}")
            self.log.emit(f"Error: {error_msg}")
            self.error.emit(error_msg)
        finally:
            self._logger.debug("Download worker run completed")
            self._is_running = False
            self.cleanup()

    def wait(self):
        """等待下载完成"""
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join()

    def _process_pipe_output(self):
        """处理管道输出的线程函数"""
        while not self._cancel_event.is_set():
            if self._pipe_reader.poll(0.1):
                try:
                    output = self._pipe_reader.recv()
                    if output == "DOWNLOAD_COMPLETE":
                        break
                    self.log.emit(output)
                except EOFError:
                    break
                except Exception as e:
                    self._logger.error(f"Error processing pipe output: {e}")
                    continue

    def cleanup(self):
        """清理资源和临时文件"""
        try:
            self._logger.debug("Starting cleanup")
            # 保存当前的 endpoint 设置
            current_endpoint = os.environ.get('HF_ENDPOINT')
            
            # 清理环境变量
            cleanup_environment()
            
            # 恢复 endpoint 设置
            if current_endpoint:
                os.environ['HF_ENDPOINT'] = current_endpoint
            
            self._logger.debug("Environment cleanup complete")
            
            # 移除日志处理器
            if self.log_handler in logger.handlers:
                logger.removeHandler(self.log_handler)
            if self.log_handler in self._logger.handlers:
                self._logger.removeHandler(self.log_handler)
            if self.log_handler in qt_logger.handlers:
                qt_logger.removeHandler(self.log_handler)
            self._logger.debug("Log handlers removed")
            
            # 清理锁文件
            cleanup_lock_files(self.model_dir)
            self._logger.debug("Lock files cleaned up")
            
        except Exception as e:
            self._logger.exception("Error during cleanup")
            self.log.emit(f"Warning: Cleanup error: {str(e)}")
