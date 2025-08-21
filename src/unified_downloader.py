"""
Unified downloader for multiple model hub platforms
Simple configuration-driven approach without over-engineering
"""

import logging
import multiprocessing
import os
import signal
import sys
import threading
import time
import weakref

from PyQt6.QtCore import QMutex, QMutexLocker, QObject, QThread, QTimer, pyqtSignal
from tqdm.auto import tqdm

from .utils import cleanup_environment, cleanup_lock_files

# Platform configurations - simple dictionary approach
PLATFORM_CONFIGS = {
    "huggingface": {
        "token_env": "HF_TOKEN",
        "endpoint_env": "HF_ENDPOINT",
        "logger_name": "huggingface_hub",
        "default_endpoint": "https://huggingface.co",
        "mirror_endpoint": "https://hf-mirror.com",
        "ssl_verification": True,
    },
    "modelscope": {
        "token_env": "MODELSCOPE_API_TOKEN",
        "endpoint_env": "MODELSCOPE_ENDPOINT",
        "logger_name": "modelscope",
        "default_endpoint": "https://modelscope.cn",
        "mirror_endpoint": "https://modelscope.cn",
        "ssl_verification": True,
    },
}


class LoggerManager:
    """Unified logger handler management to prevent memory leaks"""

    _instance = None
    _handlers = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_handler(self, signal):
        """Get or create log handler"""
        handler_id = id(signal)
        if handler_id not in self._handlers:
            self._handlers[handler_id] = LogHandler(signal)
        return self._handlers[handler_id]

    def cleanup_handler(self, signal):
        """Safely cleanup log handler"""
        handler_id = id(signal)
        if handler_id in self._handlers:
            handler = self._handlers.pop(handler_id)
            for config in PLATFORM_CONFIGS.values():
                logger_name = config["logger_name"]
                target_logger = logging.getLogger(logger_name)
                if handler in target_logger.handlers:
                    target_logger.removeHandler(handler)
            for logger_name in ["UnifiedDownloadWorker", "PyQt6"]:
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
        if hasattr(pipe, "send"):
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

        if "\r" in text:
            self.buffer = text.split("\r")[-1]
            if self.buffer.strip() and self.buffer != self.last_progress:
                self.send(self.buffer)
                self.last_progress = self.buffer
        elif "\n" in text:
            self.buffer += text
            lines = self.buffer.split("\n")
            self.buffer = lines[-1]
            for line in lines[:-1]:
                if (
                    line.strip() and line != self.last_progress
                ):
                    self.send(line)
        else:
            self.buffer += text

    def flush(self):
        if (
            not self._closed
            and self.buffer.strip()
            and self.buffer != self.last_progress
        ):
            self.send(self.buffer)
            self.buffer = ""

    def close(self):
        """Close the pipe writer"""
        self._closed = True
        self.pipe = None


def download_huggingface(
    model_id: str,
    save_path: str,
    token: str = None,
    endpoint: str = None,
    pipe=None,
    repo_type: str = "model",
):
    """HuggingFace platform-specific download logic"""
    try:
        from huggingface_hub import HfFolder, snapshot_download
    except ImportError:
        if pipe:
            pipe.send(
                "Error: HuggingFace Hub library not installed. Please install with: pip install huggingface_hub"
            )
        return False

    if token:
        HfFolder.save_token(token)
        os.environ["HF_TOKEN"] = token

    if endpoint:
        os.environ["HF_ENDPOINT"] = endpoint
        if "hf-mirror.com" in endpoint:
            os.environ["HF_HUB_DISABLE_SSL_VERIFICATION"] = "1"
        else:
            os.environ.pop("HF_HUB_DISABLE_SSL_VERIFICATION", None)
    else:
        os.environ.pop("HF_HUB_DISABLE_SSL_VERIFICATION", None)

    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
    os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "300"
    os.environ["HF_HUB_ENABLE_CONCURRENT_DOWNLOAD"] = "1"

    repo_dir = os.path.join(save_path, model_id.split("/")[-1])

    if pipe:
        pipe.send(f"Starting HuggingFace download of {model_id}")

    cpu_count = multiprocessing.cpu_count()
    max_workers = min(cpu_count + 2, 8)

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
        proxies=None,
        endpoint=endpoint,
    )

    if pipe:
        pipe.send(f"HuggingFace download completed: {result}")

    return True


def download_modelscope(
    model_id: str,
    save_path: str,
    token: str = None,
    endpoint: str = None,
    pipe=None,
    repo_type: str = "model",
):
    """ModelScope platform-specific download logic"""
    try:
        from modelscope import HubApi, MsDataset
        from modelscope.hub.snapshot_download import snapshot_download
    except ImportError:
        if pipe:
            pipe.send(
                "Error: ModelScope library not installed. Please install with: uv add modelscope"
            )
        return False

    if token:
        try:
            api = HubApi()
            api.login(token)
            if pipe:
                pipe.send("ModelScope authentication successful")
        except Exception as e:
            if pipe:
                pipe.send(f"ModelScope authentication failed: {e!s}")

    if endpoint:
        os.environ["MODELSCOPE_ENDPOINT"] = endpoint

    repo_name = model_id.split("/")[-1]
    repo_dir = os.path.join(save_path, repo_name)

    if pipe:
        pipe.send(f"Starting ModelScope download of {model_id}")
        if repo_type == "dataset":
            pipe.send(
                f"Downloading Dataset from https://www.modelscope.cn to directory: {repo_dir}"
            )
        else:
            pipe.send(
                f"Downloading Model from https://www.modelscope.cn to directory: {repo_dir}"
            )

    try:
        if repo_type == "dataset":
            if pipe:
                pipe.send("Using MsDataset for dataset download...")

            os.makedirs(repo_dir, exist_ok=True)

            dataset = MsDataset.load(
                dataset_name=model_id,
                cache_dir=repo_dir,
            )

            if pipe:
                pipe.send(f"ModelScope dataset loaded and cached to: {repo_dir}")

            result = repo_dir
        else:
            result = snapshot_download(
                model_id=model_id,
                local_dir=repo_dir,
                revision="master",
                ignore_patterns=[
                    "*.h5",
                    "*.ot",
                    "*.msgpack",
                    "*.bin",
                    "*.pkl",
                    "*.onnx",
                    ".*",
                ],
            )

        if pipe:
            pipe.send(f"ModelScope download completed: {result}")

        return True

    except Exception as e:
        error_msg = f"ModelScope download failed: {e!s}"
        if pipe:
            pipe.send(error_msg)
        print(f"Error: {error_msg}")
        return False


def unified_download_model(
    platform: str,
    model_id: str,
    save_path: str,
    token: str = None,
    endpoint: str = None,
    pipe=None,
    repo_type: str = "model",
):
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

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        if pipe:
            sys.stdout = pipe
            sys.stderr = pipe

        def signal_handler(signum, frame):
            if pipe:
                pipe.send("Download interrupted by signal")
            sys.exit(1)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        try:
            success = False
            if platform == "huggingface":
                success = download_huggingface(
                    model_id, save_path, token, endpoint, pipe, repo_type
                )
            elif platform == "modelscope":
                success = download_modelscope(
                    model_id, save_path, token, endpoint, pipe, repo_type
                )
            else:
                if pipe:
                    pipe.send(f"Error: Unsupported platform '{platform}'")
                return False

            if not success:
                if pipe:
                    pipe.send(f"Error: {platform} download failed")
                sys.exit(1)

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
                if (
                    parent is None
                    or not hasattr(parent, "isRunning")
                    or not parent.isRunning()
                ):
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

    def __init__(
        self,
        platform,
        model_id,
        save_path,
        token=None,
        endpoint=None,
        repo_type="model",
    ):
        super().__init__()

        if platform not in PLATFORM_CONFIGS:
            raise ValueError(
                f"Unsupported platform: {platform}. Supported: {list(PLATFORM_CONFIGS.keys())}"
            )

        self.platform = platform
        self.model_id = model_id
        self.save_path = save_path
        self.token = token
        self.repo_type = repo_type

        # Get platform configuration
        self._config = PLATFORM_CONFIGS[platform]
        self.endpoint = endpoint if endpoint else self._config["default_endpoint"]

        # Create thread-safe signal emitter
        self._signal_emitter = ThreadSafeSignalEmitter(self)

        # Expose signals through the emitter
        self.finished = self._signal_emitter.finished
        self.error = self._signal_emitter.error
        self.status = self._signal_emitter.status
        self.log = self._signal_emitter.log

        self._logger = logging.getLogger("UnifiedDownloadWorker")
        self._logger.setLevel(logging.DEBUG)

        self.logger_manager = LoggerManager()
        self.log_handler = self.logger_manager.get_handler(self.log)
        self.log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

        platform_logger = logging.getLogger(self._config["logger_name"])
        platform_logger.addHandler(self.log_handler)
        self._logger.addHandler(self.log_handler)
        qt_logger = logging.getLogger("PyQt6")
        qt_logger.addHandler(self.log_handler)

        self.repo_name = self.model_id.split("/")[-1]
        self.repo_dir = os.path.join(self.save_path, self.repo_name)
        self._logger.debug(
            f"Initialized {platform} worker for {repo_type} {model_id} with save path {save_path}"
        )

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
    def _isolated_download_wrapper(
        platform, model_id, save_path, token, endpoint, pipe, repo_type
    ):
        """Process-isolated download wrapper that doesn't inherit PyQt state"""
        try:
            # Create safe pipe writer in the new process
            safe_pipe = SafePipeWriter(pipe)

            # Call the unified download function
            result = unified_download_model(
                platform, model_id, save_path, token, endpoint, safe_pipe, repo_type
            )

            # Clean up pipe
            safe_pipe.close()

            return result
        except Exception as e:
            if pipe:
                try:
                    pipe.send(f"Process wrapper error: {e!s}")
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
        """Cancel download"""
        if not self.isRunning():
            return

        self._logger.debug(f"Cancel {self.platform} download requested")

        self._cancel_event.set()

        if self._output_thread and self._output_thread.is_alive():
            try:
                self._output_thread.join(timeout=1.0)
            except Exception as e:
                self._logger.error(f"Error stopping output thread: {e}")

        if self._download_process and self._download_process.is_alive():
            try:
                self._download_process.terminate()
                for _ in range(30):
                    if not self._download_process.is_alive():
                        break
                    time.sleep(0.1)

                if self._download_process.is_alive():
                    try:
                        self._download_process.kill()
                        time.sleep(0.1)
                    except:
                        pass

                self._logger.debug(f"{self.platform} download process terminated")
            except Exception as e:
                self._logger.error(
                    f"Error terminating {self.platform} download process: {e}"
                )

        if hasattr(self, "_signal_emitter"):
            self._signal_emitter.invalidate()

        self.cleanup()
        self._is_running = False

        if hasattr(self, "_cleanup_timer") and self._cleanup_timer:
            self._cleanup_timer.stop()
            self._cleanup_timer.deleteLater()

        self._cleanup_timer = QTimer()
        self._cleanup_timer.setSingleShot(True)
        self._cleanup_timer.timeout.connect(self.quit)
        self._cleanup_timer.start(100)

    def _run(self):
        """Run download task in isolated thread"""
        try:
            self._logger.debug(f"Starting {self.platform} download worker run")
            cleanup_lock_files(self.repo_dir)

            repo_type_text = "model" if self.repo_type == "model" else "dataset"
            self._safe_emit(
                "status",
                f"Downloading {self.platform} {repo_type_text} repository to {self.repo_dir}...",
            )
            self._safe_emit(
                "log",
                f"Starting {self.platform} download of {self.model_id} to {self.repo_dir}",
            )

            self._pipe_reader, self._pipe_writer = multiprocessing.Pipe(duplex=False)

            self._output_thread = threading.Thread(
                target=self._process_pipe_output, daemon=True
            )
            self._output_thread.start()

            self._download_process = multiprocessing.get_context("spawn").Process(
                target=self._isolated_download_wrapper,
                args=(
                    self.platform,
                    self.model_id,
                    self.save_path,
                    self.token,
                    self.endpoint,
                    self._pipe_writer,
                    self.repo_type,
                ),
            )
            self._download_process.start()

            download_completed = False
            while self._download_process.is_alive():
                if self._cancel_event.is_set():
                    self._logger.debug("Cancel event detected, terminating process")
                    self._download_process.terminate()
                    break
                self._download_process.join(timeout=0.1)

            if self._download_process.exitcode == 0:
                download_completed = True
            else:
                self._logger.debug(
                    f"{self.platform} download process exited with code: {self._download_process.exitcode}"
                )

            self._cancel_event.set()
            if self._output_thread:
                self._output_thread.join()

            if download_completed:
                cleanup_lock_files(self.repo_dir)
                repo_type_text = "Model" if self.repo_type == "model" else "Dataset"
                self._safe_emit(
                    "log",
                    f"{self.platform} {repo_type_text} downloaded successfully to: {self.repo_dir}",
                )
                self._logger.debug(f"{self.platform} download completed successfully")
                self._safe_emit("finished")
            elif self._cancel_event.is_set() and not download_completed:
                raise Exception(f"{self.platform} download cancelled by user")
            else:
                raise Exception(f"{self.platform} download process failed")

        except Exception as e:
            error_msg = str(e)
            self._logger.error(f"{self.platform} download failed: {error_msg}")
            self._safe_emit("log", f"{self.platform} Error: {error_msg}")
            self._safe_emit("error", error_msg)
        finally:
            self._logger.debug(f"{self.platform} download worker run completed")
            self._is_running = False
            if hasattr(self, "_cancel_event"):
                self._cancel_event.set()
            if (
                hasattr(self, "_output_thread")
                and self._output_thread
                and self._output_thread.is_alive()
            ):
                self._output_thread.join(timeout=1.0)
            self.cleanup()

    def _process_pipe_output(self):
        """Process pipe output in thread"""
        while not self._cancel_event.is_set():
            try:
                if self._pipe_reader and self._pipe_reader.poll(
                    0.01
                ):
                    try:
                        output = self._pipe_reader.recv()
                        if output == "DOWNLOAD_COMPLETE":
                            break
                        # Use safe signal emission
                        self._safe_emit("log", str(output))
                    except EOFError:
                        break
                    except Exception as e:
                        self._logger.error(
                            f"Error processing {self.platform} pipe output: {e}"
                        )
                        continue
            except Exception as e:
                self._logger.error(f"Critical error in pipe output processing: {e}")
                break

    def cleanup(self):
        """Enhanced resource cleanup ensuring complete release"""
        cleanup_errors = []

        try:
            self._logger.debug(f"Starting {self.platform} comprehensive cleanup")

            current_endpoint = os.environ.get(self._config["endpoint_env"])

            try:
                cleanup_environment()
                os.environ.pop(self._config["token_env"], None)
                os.environ.pop(self._config["endpoint_env"], None)
                if self.platform == "huggingface":
                    os.environ.pop("HF_HUB_DISABLE_SSL_VERIFICATION", None)
                    os.environ.pop("HF_HUB_ENABLE_HF_TRANSFER", None)
                    os.environ.pop("HF_HUB_DOWNLOAD_TIMEOUT", None)
                    os.environ.pop("HF_HUB_ENABLE_CONCURRENT_DOWNLOAD", None)
                self._logger.debug(f"{self.platform} environment variables cleaned")
            except Exception as e:
                cleanup_errors.append(
                    f"{self.platform} environment cleanup failed: {e}"
                )

            if current_endpoint:
                os.environ[self._config["endpoint_env"]] = current_endpoint

            try:
                if hasattr(self, "_pipe_reader") and self._pipe_reader:
                    self._pipe_reader.close()
                if hasattr(self, "_pipe_writer") and self._pipe_writer:
                    self._pipe_writer.close()
                self._logger.debug(f"{self.platform} pipe connections closed")
            except Exception as e:
                cleanup_errors.append(f"{self.platform} pipe cleanup failed: {e}")

            try:
                if hasattr(self, "logger_manager"):
                    self.logger_manager.cleanup_handler(self.log)
                    self._logger.debug(f"{self.platform} log handlers removed")
            except Exception as e:
                cleanup_errors.append(
                    f"{self.platform} log handler cleanup failed: {e}"
                )

            try:
                cleanup_lock_files(self.repo_dir)
                self._logger.debug(f"{self.platform} lock files cleaned up")
            except Exception as e:
                cleanup_errors.append(f"{self.platform} lock file cleanup failed: {e}")

            self._is_running = False
            self._download_process = None
            self._pipe_reader = None
            self._pipe_writer = None
            self._output_thread = None

            try:
                if hasattr(self, "_signal_emitter"):
                    self._signal_emitter.invalidate()
                    self._logger.debug(f"{self.platform} signal emitter invalidated")
            except Exception as e:
                cleanup_errors.append(
                    f"{self.platform} signal emitter cleanup failed: {e}"
                )

            if cleanup_errors:
                error_summary = "; ".join(cleanup_errors)
                self._logger.warning(
                    f"{self.platform} cleanup completed with errors: {error_summary}"
                )
                try:
                    self._safe_emit(
                        "log",
                        f"Warning: Some {self.platform} cleanup operations failed: {error_summary}",
                    )
                except:
                    pass
            else:
                self._logger.debug(f"{self.platform} cleanup completed successfully")

        except Exception as e:
            self._logger.exception(f"Critical error during {self.platform} cleanup")
            try:
                self._safe_emit("log", f"Critical {self.platform} cleanup error: {e!s}")
            except:
                pass
