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

class LoggerManager:
    """统一管理日志处理器，防止内存泄漏"""
    _instance = None
    _handlers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_handler(self, signal):
        """获取或创建日志处理器"""
        handler_id = id(signal)
        if handler_id not in self._handlers:
            self._handlers[handler_id] = LogHandler(signal)
        return self._handlers[handler_id]
    
    def cleanup_handler(self, signal):
        """安全清理日志处理器"""
        handler_id = id(signal)
        if handler_id in self._handlers:
            handler = self._handlers.pop(handler_id)
            # 从所有相关logger中移除
            for logger_name in ['huggingface_hub', 'DownloadWorker', 'PyQt6']:
                target_logger = logging.getLogger(logger_name)
                if handler in target_logger.handlers:
                    target_logger.removeHandler(handler)
    
    def get_active_handlers_count(self):
        """获取活跃处理器数量（用于监控）"""
        return len(self._handlers)

class DownloadProgressBar(tqdm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current = self.n

    def update(self, n):
        super().update(n)
        self._current += n

def download_model(model_id: str, save_path: str, token: str = None, endpoint: str = None, pipe=None, repo_type: str = "model"):
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
        repo_dir = os.path.join(save_path, model_id.split('/')[-1])
        
        # 设置信号处理，确保可以正确响应终止信号
        def signal_handler(signum, frame):
            if pipe:
                pipe.send("Download interrupted by signal")
            sys.exit(1)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            # 优化线程数计算：I/O密集型任务使用CPU核心数+2，避免过度配置
            cpu_count = multiprocessing.cpu_count()
            max_workers = min(cpu_count + 2, 8)  # 最多8个并发连接
            
            result = snapshot_download(
                repo_id=model_id,
                repo_type=repo_type,
                local_dir=repo_dir,
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
    
    def __init__(self, model_id, save_path, token=None, endpoint=None, repo_type="model"):
        super().__init__()
        self.model_id = model_id
        self.save_path = save_path
        self.token = token
        self.endpoint = endpoint if endpoint else "https://huggingface.co"
        self.repo_type = repo_type
        
        # 设置日志
        self._logger = logging.getLogger("DownloadWorker")
        self._logger.setLevel(logging.DEBUG)
        
        # 使用统一日志管理器
        self.logger_manager = LoggerManager()
        self.log_handler = self.logger_manager.get_handler(self.log)
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(self.log_handler)
        self._logger.addHandler(self.log_handler)
        qt_logger.addHandler(self.log_handler)

        # 保存仓库目录路径
        self.repo_name = self.model_id.split('/')[-1]
        self.repo_dir = os.path.join(self.save_path, self.repo_name)
        self._logger.debug(f"Initialized worker for {repo_type} {model_id} with save path {save_path}")
        
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
                
                # 如果进程还在运行，渐进式强制终止
                if self._download_process.is_alive():
                    self._logger.warning("Process not responding to terminate, applying progressive force")
                    try:
                        import psutil
                        parent = psutil.Process(self._download_process.pid)
                        
                        # 首先尝试终止子进程
                        for child in parent.children(recursive=True):
                            try:
                                child.terminate()
                                child.wait(timeout=1)  # 等待1秒
                            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                                try:
                                    child.kill()  # 子进程无响应时强制终止
                                except psutil.NoSuchProcess:
                                    pass
                        
                        # 然后终止父进程
                        try:
                            parent.wait(timeout=2)  # 等待2秒让进程自然退出
                        except psutil.TimeoutExpired:
                            parent.kill()  # 最后手段：强制终止
                            
                    except psutil.NoSuchProcess:
                        pass  # 进程已经不存在
                    except Exception as e:
                        self._logger.error(f"Error in progressive process termination: {e}")
                        # 最后的fallback：直接kill
                        try:
                            self._download_process.kill()
                        except:
                            pass
                
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
            cleanup_lock_files(self.repo_dir)
            
            repo_type_text = "model" if self.repo_type == "model" else "dataset"
            self.status.emit(f"Downloading {repo_type_text} repository to {self.repo_dir}...")
            self.log.emit(f"Starting download of {self.model_id} to {self.repo_dir}")

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
                args=(self.model_id, self.save_path, self.token, self.endpoint, pipe_writer, self.repo_type)
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
                cleanup_lock_files(self.repo_dir)
                repo_type_text = "Model" if self.repo_type == "model" else "Dataset"
                self.log.emit(f"{repo_type_text} downloaded successfully to: {self.repo_dir}")
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
            if self._pipe_reader.poll(0.01):  # 降低轮询间隔至10ms提升响应性
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
        """增强的资源清理，确保完全释放"""
        cleanup_errors = []
        
        try:
            self._logger.debug("Starting comprehensive cleanup")
            
            # 1. 保存当前的 endpoint 设置
            current_endpoint = os.environ.get('HF_ENDPOINT')
            
            # 2. 清理环境变量
            try:
                cleanup_environment()
                self._logger.debug("Environment variables cleaned")
            except Exception as e:
                cleanup_errors.append(f"Environment cleanup failed: {e}")
            
            # 3. 恢复 endpoint 设置
            if current_endpoint:
                os.environ['HF_ENDPOINT'] = current_endpoint
            
            # 4. 清理管道连接
            try:
                if hasattr(self, '_pipe_reader') and self._pipe_reader:
                    self._pipe_reader.close()
                if hasattr(self, '_pipe_writer') and self._pipe_writer:
                    self._pipe_writer.close()
                self._logger.debug("Pipe connections closed")
            except Exception as e:
                cleanup_errors.append(f"Pipe cleanup failed: {e}")
            
            # 5. 使用统一管理器清理日志处理器
            try:
                if hasattr(self, 'logger_manager'):
                    self.logger_manager.cleanup_handler(self.log)
                    self._logger.debug("Log handlers removed")
            except Exception as e:
                cleanup_errors.append(f"Log handler cleanup failed: {e}")
            
            # 6. 清理锁文件
            try:
                cleanup_lock_files(self.repo_dir)
                self._logger.debug("Lock files cleaned up")
            except Exception as e:
                cleanup_errors.append(f"Lock file cleanup failed: {e}")
            
            # 7. 重置内部状态
            self._is_running = False
            self._download_process = None
            self._pipe_reader = None
            self._pipe_writer = None
            self._output_thread = None
            
            if cleanup_errors:
                error_summary = "; ".join(cleanup_errors)
                self._logger.warning(f"Cleanup completed with errors: {error_summary}")
                self.log.emit(f"Warning: Some cleanup operations failed: {error_summary}")
            else:
                self._logger.debug("Cleanup completed successfully")
                
        except Exception as e:
            self._logger.exception("Critical error during cleanup")
            self.log.emit(f"Critical cleanup error: {str(e)}")
