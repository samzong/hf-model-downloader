"""
Unified downloader for multiple model hub platforms
Simple configuration-driven approach without over-engineering
"""

import os
import json
import logging
import signal
import threading
import sys
import time
import weakref
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional, Callable
import multiprocessing
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer, Qt, QMutex, QMutexLocker
from .utils import cleanup_lock_files, cleanup_environment
from tqdm.auto import tqdm

# Platform configurations - simple dictionary approach
PLATFORM_CONFIGS = {
    'huggingface': {
        'token_env': 'HF_TOKEN',
        'endpoint_env': 'HF_ENDPOINT', 
        'logger_name': 'huggingface_hub',
        'default_endpoint': 'https://huggingface.co',
        'mirror_endpoint': 'https://hf-mirror.com',
        'ssl_verification': True
    },
    'modelscope': {
        'token_env': 'MODELSCOPE_API_TOKEN',
        'endpoint_env': 'MODELSCOPE_ENDPOINT',
        'logger_name': 'modelscope', 
        'default_endpoint': 'https://modelscope.cn',
        'mirror_endpoint': 'https://modelscope.cn',
        'ssl_verification': True
    }
}

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
            for config in PLATFORM_CONFIGS.values():
                logger_name = config['logger_name']
                target_logger = logging.getLogger(logger_name)
                if handler in target_logger.handlers:
                    target_logger.removeHandler(handler)
            # 清理其他日志
            for logger_name in ['UnifiedDownloadWorker', 'PyQt6']:
                target_logger = logging.getLogger(logger_name)
                if handler in target_logger.handlers:
                    target_logger.removeHandler(handler)

class LogHandler(logging.Handler):
    def __init__(self, log_signal):
        super().__init__()
        self.log_signal = log_signal

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_signal.emit(msg)
        except RuntimeError:
            # Signal target has been destroyed, ignore
            pass

class UnifiedProgressBar(tqdm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current = self.n

    def update(self, n):
        super().update(n)
        self._current += n

class SafePipeWriter:
    """Process-safe pipe writer that doesn't hold PyQt references"""
    def __init__(self, pipe):
        if hasattr(pipe, 'send'):
            self.pipe = pipe
        else:
            # Create a simple wrapper for non-pipe objects
            self.pipe = None
        self.buffer = ""
        self.last_progress = ""
        self._closed = False
    
    def send(self, message):
        """Send message through pipe with error handling"""
        if self._closed or not self.pipe:
            return
        try:
            self.pipe.send(str(message))
        except (BrokenPipeError, OSError, EOFError):
            self._closed = True
    
    def write(self, text):
        if self._closed:
            return
            
        # 处理所有输出，包括进度条
        if '\r' in text:  # 进度条更新
            # 清除旧的进度信息
            self.buffer = text.split('\r')[-1]
            if self.buffer.strip() and self.buffer != self.last_progress:
                self.send(self.buffer)
                self.last_progress = self.buffer
        elif '\n' in text:  # 普通日志输出
            self.buffer += text
            lines = self.buffer.split('\n')
            self.buffer = lines[-1]  # 保留最后一个不完整的行
            for line in lines[:-1]:
                if line.strip() and line != self.last_progress:  # 避免重复发送相同的进度信息
                    self.send(line)
        else:
            self.buffer += text
    
    def flush(self):
        if not self._closed and self.buffer.strip() and self.buffer != self.last_progress:
            self.send(self.buffer)
            self.buffer = ""
            
    def close(self):
        """Close the pipe writer"""
        self._closed = True
        self.pipe = None

def download_huggingface(model_id: str, save_path: str, token: str = None, endpoint: str = None, pipe=None, repo_type: str = "model"):
    """HuggingFace platform-specific download logic"""
    try:
        from huggingface_hub import HfFolder, snapshot_download
    except ImportError as e:
        if pipe:
            pipe.send("Error: HuggingFace Hub library not installed. Please install with: pip install huggingface_hub")
        return False
    
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
    
    if pipe:
        pipe.send(f"Starting HuggingFace download of {model_id}")
    
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
        tqdm_class=UnifiedProgressBar,
        ignore_patterns=["*.h5", "*.ot", "*.msgpack", "*.bin", "*.pkl", "*.onnx", ".*"],
        local_files_only=False,
        etag_timeout=30,
        proxies=None,  # 不使用代理
        endpoint=endpoint
    )
    
    if pipe:
        pipe.send(f"HuggingFace download completed: {result}")
    
    return True

def download_modelscope(model_id: str, save_path: str, token: str = None, endpoint: str = None, pipe=None, repo_type: str = "model"):
    """ModelScope platform-specific download logic"""
    try:
        from modelscope import snapshot_download
    except ImportError as e:
        if pipe:
            pipe.send(f"Error: ModelScope library not installed. Please install with: uv add modelscope")
        return False
    
    # 设置 token
    if token:
        os.environ['MODELSCOPE_API_TOKEN'] = token
    
    # 设置 endpoint
    if endpoint:
        os.environ['MODELSCOPE_ENDPOINT'] = endpoint
    
    # 执行下载
    repo_dir = os.path.join(save_path, model_id.split('/')[-1])
    
    if pipe:
        pipe.send(f"Starting ModelScope download of {model_id}")
    
    # 使用 ModelScope 的 snapshot_download
    result = snapshot_download(
        model_id=model_id,
        cache_dir=repo_dir,
        revision='master',  # 默认使用 master 分支
        repo_type=repo_type,  # 添加 repo_type 参数支持数据集下载
        ignore_file_pattern=["*.h5", "*.ot", "*.msgpack", "*.bin", "*.pkl", "*.onnx", ".*"]
    )
    
    if pipe:
        pipe.send(f"ModelScope download completed: {result}")
    
    return True

def unified_download_model(platform: str, model_id: str, save_path: str, token: str = None, endpoint: str = None, pipe=None, repo_type: str = "model"):
    """Unified download function that delegates to platform-specific implementations"""
    try:
        config = PLATFORM_CONFIGS[platform]
        
        print(f"\n=== {platform.title()} Download Process Debug Info ===")
        print("Process ID:", os.getpid())
        print("Parent Process ID:", os.getppid())
        print("Current Working Directory:", os.getcwd())
        print("Python Executable:", sys.executable)
        print("Process Start Method:", multiprocessing.get_start_method())
        print("=== End Debug Info ===\n")

        # 重定向标准输出和标准错误
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        if pipe:
            sys.stdout = pipe
            sys.stderr = pipe
        
        # 设置信号处理，确保可以正确响应终止信号
        def signal_handler(signum, frame):
            if pipe:
                pipe.send("Download interrupted by signal")
            sys.exit(1)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            # 根据平台调用相应的下载函数
            success = False
            if platform == 'huggingface':
                success = download_huggingface(model_id, save_path, token, endpoint, pipe, repo_type)
            elif platform == 'modelscope':
                success = download_modelscope(model_id, save_path, token, endpoint, pipe, repo_type)
            else:
                if pipe:
                    pipe.send(f"Error: Unsupported platform '{platform}'")
                return False
            
            # 如果下载失败，确保进程以错误退出
            if not success:
                if pipe:
                    pipe.send(f"Error: {platform} download failed")
                sys.exit(1)  # 确保进程以错误退出码退出
            
            return success
                
        except KeyboardInterrupt:
            if pipe:
                pipe.send("Download cancelled by user")
            return False
        
    except Exception as e:
        error_msg = str(e)
        if pipe:
            pipe.send(f"Error during {platform} download: {error_msg}")
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

class ThreadSafeSignalEmitter(QObject):
    """Thread-safe signal emitter with object lifecycle management"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    status = pyqtSignal(str)
    log = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._mutex = QMutex()
        self._is_valid = True
        self._parent_ref = weakref.ref(parent) if parent else None
        
    def safe_emit(self, signal_name: str, *args):
        """Thread-safe signal emission with object validity checks"""
        with QMutexLocker(self._mutex):
            if not self._is_valid:
                return False
                
            # Check parent object validity
            if self._parent_ref:
                parent = self._parent_ref()
                if parent is None or not hasattr(parent, 'isRunning') or not parent.isRunning():
                    return False
            
            try:
                signal = getattr(self, signal_name, None)
                if signal is not None:
                    # Use QueuedConnection for cross-thread safety
                    signal.emit(*args)
                    return True
            except (RuntimeError, AttributeError):
                # Signal target destroyed or unavailable
                self._is_valid = False
                return False
        return False
    
    def invalidate(self):
        """Mark this emitter as invalid to prevent further emissions"""
        with QMutexLocker(self._mutex):
            self._is_valid = False

class UnifiedDownloadWorker(QThread):
    """Unified download worker supporting multiple platforms via configuration"""
    
    def __init__(self, platform, model_id, save_path, token=None, endpoint=None, repo_type="model"):
        super().__init__()
        
        if platform not in PLATFORM_CONFIGS:
            raise ValueError(f"Unsupported platform: {platform}. Supported: {list(PLATFORM_CONFIGS.keys())}")
        
        self.platform = platform
        self.model_id = model_id
        self.save_path = save_path
        self.token = token
        self.repo_type = repo_type
        
        # Get platform configuration
        self._config = PLATFORM_CONFIGS[platform]
        self.endpoint = endpoint if endpoint else self._config['default_endpoint']
        
        # Create thread-safe signal emitter
        self._signal_emitter = ThreadSafeSignalEmitter(self)
        
        # Expose signals through the emitter
        self.finished = self._signal_emitter.finished
        self.error = self._signal_emitter.error
        self.status = self._signal_emitter.status
        self.log = self._signal_emitter.log
        
        # 设置日志
        self._logger = logging.getLogger("UnifiedDownloadWorker")
        self._logger.setLevel(logging.DEBUG)
        
        # 使用统一日志管理器
        self.logger_manager = LoggerManager()
        self.log_handler = self.logger_manager.get_handler(self.log)
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        # 添加处理器到相关日志记录器
        platform_logger = logging.getLogger(self._config['logger_name'])
        platform_logger.addHandler(self.log_handler)
        self._logger.addHandler(self.log_handler)
        qt_logger = logging.getLogger("PyQt6")
        qt_logger.addHandler(self.log_handler)

        # 保存仓库目录路径
        self.repo_name = self.model_id.split('/')[-1]
        self.repo_dir = os.path.join(self.save_path, self.repo_name)
        self._logger.debug(f"Initialized {platform} worker for {repo_type} {model_id} with save path {save_path}")
        
        # 添加取消事件和进程引用
        self._cancel_event = threading.Event()
        self._download_process = None
        self._pipe_reader = None
        self._pipe_writer = None
        self._output_thread = None
        self._is_running = False
        self._cleanup_timer = None
        
    def _safe_emit(self, signal_name: str, *args):
        """Safe signal emission wrapper"""
        return self._signal_emitter.safe_emit(signal_name, *args)

    @staticmethod
    def _isolated_download_wrapper(platform, model_id, save_path, token, endpoint, pipe, repo_type):
        """Process-isolated download wrapper that doesn't inherit PyQt state"""
        try:
            # Create safe pipe writer in the new process
            safe_pipe = SafePipeWriter(pipe)
            
            # Call the unified download function
            result = unified_download_model(platform, model_id, save_path, token, endpoint, safe_pipe, repo_type)
            
            # Clean up pipe
            safe_pipe.close()
            
            return result
        except Exception as e:
            if pipe:
                try:
                    pipe.send(f"Process wrapper error: {str(e)}")
                except:
                    pass
            return False

    def run(self):
        """QThread run method - this executes in the worker thread"""
        try:
            self._is_running = True
            self._cancel_event.clear()
            self._run()
        finally:
            self._is_running = False

    def cancel_download(self):
        """取消下载"""
        if not self.isRunning():
            return

        self._logger.debug(f"Cancel {self.platform} download requested")
        
        # 设置取消事件
        self._cancel_event.set()
        
        # 停止输出处理线程
        if self._output_thread and self._output_thread.is_alive():
            try:
                self._output_thread.join(timeout=1.0)
            except Exception as e:
                self._logger.error(f"Error stopping output thread: {e}")
        
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
                    try:
                        self._download_process.kill()
                        # 再等待一小段时间确保进程完全终止
                        time.sleep(0.1)
                    except:
                        pass
                
                self._logger.debug(f"{self.platform} download process terminated")
            except Exception as e:
                self._logger.error(f"Error terminating {self.platform} download process: {e}")
        
        # 无效化信号发射器
        if hasattr(self, '_signal_emitter'):
            self._signal_emitter.invalidate()
        
        # 清理环境和文件
        self.cleanup()
        self._is_running = False
        
        # 使用延迟退出避免Qt对象竞态条件
        if hasattr(self, '_cleanup_timer') and self._cleanup_timer:
            self._cleanup_timer.stop()
            self._cleanup_timer.deleteLater()
            
        self._cleanup_timer = QTimer()
        self._cleanup_timer.setSingleShot(True)
        self._cleanup_timer.timeout.connect(self.quit)
        self._cleanup_timer.start(100)  # 100ms延迟

    def _run(self):
        """在独立线程中运行下载任务"""
        try:
            self._logger.debug(f"Starting {self.platform} download worker run")
            # 清理现有的锁文件
            cleanup_lock_files(self.repo_dir)
            
            repo_type_text = "model" if self.repo_type == "model" else "dataset"
            self._safe_emit('status', f"Downloading {self.platform} {repo_type_text} repository to {self.repo_dir}...")
            self._safe_emit('log', f"Starting {self.platform} download of {self.model_id} to {self.repo_dir}")

            # 创建进程安全的管道通信
            self._pipe_reader, self._pipe_writer = multiprocessing.Pipe(duplex=False)
            
            # 启动输出处理线程
            self._output_thread = threading.Thread(target=self._process_pipe_output, daemon=True)
            self._output_thread.start()

            # 在新进程中启动下载任务 - 只传递原始pipe对象
            self._download_process = multiprocessing.get_context('spawn').Process(
                target=self._isolated_download_wrapper,
                args=(self.platform, self.model_id, self.save_path, self.token, self.endpoint, self._pipe_writer, self.repo_type)
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
            else:
                # 记录进程退出码以便调试
                self._logger.debug(f"{self.platform} download process exited with code: {self._download_process.exitcode}")
            
            # 停止输出处理线程
            self._cancel_event.set()
            if self._output_thread:
                self._output_thread.join()
            
            # 处理下载结果
            if download_completed:
                cleanup_lock_files(self.repo_dir)
                repo_type_text = "Model" if self.repo_type == "model" else "Dataset"
                self._safe_emit('log', f"{self.platform} {repo_type_text} downloaded successfully to: {self.repo_dir}")
                self._logger.debug(f"{self.platform} download completed successfully")
                self._safe_emit('finished')
            elif self._cancel_event.is_set() and not download_completed:
                raise Exception(f"{self.platform} download cancelled by user")
            else:
                raise Exception(f"{self.platform} download process failed")
            
        except Exception as e:
            error_msg = str(e)
            self._logger.error(f"{self.platform} download failed: {error_msg}")
            self._safe_emit('log', f"{self.platform} Error: {error_msg}")
            self._safe_emit('error', error_msg)
        finally:
            self._logger.debug(f"{self.platform} download worker run completed")
            self._is_running = False
            # 确保停止输出处理线程
            if hasattr(self, '_cancel_event'):
                self._cancel_event.set()
            if hasattr(self, '_output_thread') and self._output_thread and self._output_thread.is_alive():
                self._output_thread.join(timeout=1.0)
            self.cleanup()


    def _process_pipe_output(self):
        """处理管道输出的线程函数"""
        while not self._cancel_event.is_set():
            try:
                if self._pipe_reader and self._pipe_reader.poll(0.01):  # 降低轮询间隔至10ms提升响应性
                    try:
                        output = self._pipe_reader.recv()
                        if output == "DOWNLOAD_COMPLETE":
                            break
                        # Use safe signal emission
                        self._safe_emit('log', str(output))
                    except EOFError:
                        break
                    except Exception as e:
                        self._logger.error(f"Error processing {self.platform} pipe output: {e}")
                        continue
            except Exception as e:
                self._logger.error(f"Critical error in pipe output processing: {e}")
                break

    def cleanup(self):
        """增强的资源清理，确保完全释放"""
        cleanup_errors = []
        
        try:
            self._logger.debug(f"Starting {self.platform} comprehensive cleanup")
            
            # 保存当前的 endpoint 设置
            current_endpoint = os.environ.get(self._config['endpoint_env'])
            
            # 清理环境变量
            try:
                cleanup_environment()
                # 清理平台特定的环境变量
                os.environ.pop(self._config['token_env'], None)
                os.environ.pop(self._config['endpoint_env'], None)
                # 清理 HuggingFace 特定的环境变量
                if self.platform == 'huggingface':
                    os.environ.pop('HF_HUB_DISABLE_SSL_VERIFICATION', None)
                    os.environ.pop('HF_HUB_ENABLE_HF_TRANSFER', None)
                    os.environ.pop('HF_HUB_DOWNLOAD_TIMEOUT', None)
                    os.environ.pop('HF_HUB_ENABLE_CONCURRENT_DOWNLOAD', None)
                self._logger.debug(f"{self.platform} environment variables cleaned")
            except Exception as e:
                cleanup_errors.append(f"{self.platform} environment cleanup failed: {e}")
            
            # 恢复 endpoint 设置
            if current_endpoint:
                os.environ[self._config['endpoint_env']] = current_endpoint
            
            # 清理管道连接
            try:
                if hasattr(self, '_pipe_reader') and self._pipe_reader:
                    self._pipe_reader.close()
                if hasattr(self, '_pipe_writer') and self._pipe_writer:
                    self._pipe_writer.close()
                self._logger.debug(f"{self.platform} pipe connections closed")
            except Exception as e:
                cleanup_errors.append(f"{self.platform} pipe cleanup failed: {e}")
            
            # 使用统一管理器清理日志处理器
            try:
                if hasattr(self, 'logger_manager'):
                    self.logger_manager.cleanup_handler(self.log)
                    self._logger.debug(f"{self.platform} log handlers removed")
            except Exception as e:
                cleanup_errors.append(f"{self.platform} log handler cleanup failed: {e}")
            
            # 清理锁文件
            try:
                cleanup_lock_files(self.repo_dir)
                self._logger.debug(f"{self.platform} lock files cleaned up")
            except Exception as e:
                cleanup_errors.append(f"{self.platform} lock file cleanup failed: {e}")
            
            # 重置内部状态
            self._is_running = False
            self._download_process = None
            self._pipe_reader = None
            self._pipe_writer = None
            self._output_thread = None
            
            # 无效化信号发射器作为最后一步
            try:
                if hasattr(self, '_signal_emitter'):
                    self._signal_emitter.invalidate()
                    self._logger.debug(f"{self.platform} signal emitter invalidated")
            except Exception as e:
                cleanup_errors.append(f"{self.platform} signal emitter cleanup failed: {e}")
            
            if cleanup_errors:
                error_summary = "; ".join(cleanup_errors)
                self._logger.warning(f"{self.platform} cleanup completed with errors: {error_summary}")
                # 最后尝试发送警告消息，如果失败则忽略
                try:
                    self._safe_emit('log', f"Warning: Some {self.platform} cleanup operations failed: {error_summary}")
                except:
                    pass
            else:
                self._logger.debug(f"{self.platform} cleanup completed successfully")
                
        except Exception as e:
            self._logger.exception(f"Critical error during {self.platform} cleanup")
            # 最后尝试发送错误消息，如果失败则忽略
            try:
                self._safe_emit('log', f"Critical {self.platform} cleanup error: {str(e)}")
            except:
                pass