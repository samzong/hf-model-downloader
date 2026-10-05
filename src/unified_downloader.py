import multiprocessing
import os
import sys
import threading

from PyQt6.QtCore import QThread, pyqtSignal

from .hf_hub_env import resolve_hf_endpoint, xet_available
from .hf_repo_validate import hf_repo_type_mismatch_message
from .utils import cleanup_lock_files


def _abort_download(pipe, message: str) -> None:
    if pipe is not None:
        pipe.send(("error", message))
    else:
        print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


class SafePipeWriter:
    def __init__(self, pipe):
        self.pipe = pipe
        self.buffer = ""
        self.last_progress = ""
        self._closed = False

    def send(self, message):
        if self._closed:
            return
        try:
            self.pipe.send(message)
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
                if line.strip() and line != self.last_progress:
                    self.send(line)
        else:
            self.buffer += text

    def flush(self):
        if self.buffer.strip() and self.buffer != self.last_progress:
            self.send(self.buffer)
        self.buffer = ""


def download_huggingface(
    model_id: str,
    save_path: str,
    token: str | None = None,
    endpoint: str | None = None,
    pipe=None,
    repo_type: str = "model",
):
    from huggingface_hub import HfApi, snapshot_download

    resolved_endpoint = resolve_hf_endpoint(endpoint)
    repo_dir = os.path.join(save_path, model_id.split("/")[-1])
    if pipe is not None:
        if not xet_available():
            pipe.send(
                "Warning: hf_xet is not available. Xet downloads may fall back to HTTP."
            )
        pipe.send("Validating repository...")
    try:
        mismatch = hf_repo_type_mismatch_message(
            HfApi(endpoint=resolved_endpoint), model_id, repo_type, token
        )
        if mismatch:
            _abort_download(pipe, mismatch)
        if pipe is not None:
            pipe.send(f"Starting HuggingFace download of {model_id}")
        return snapshot_download(
            repo_id=model_id,
            repo_type=repo_type,
            local_dir=repo_dir,
            token=token,
            max_workers=min(multiprocessing.cpu_count() + 2, 8),
            etag_timeout=30,
            endpoint=resolved_endpoint,
        )
    except Exception as exc:
        _abort_download(pipe, f"HuggingFace download failed: {exc}")


def download_modelscope(
    model_id: str,
    save_path: str,
    token: str | None = None,
    endpoint: str | None = None,
    pipe=None,
    repo_type: str = "model",
):
    from modelscope.hub.snapshot_download import snapshot_download

    repo_dir = os.path.join(save_path, model_id.split("/")[-1])
    if pipe is not None:
        pipe.send(f"Starting ModelScope download of {model_id}")
    try:
        return snapshot_download(
            repo_id=model_id,
            repo_type=repo_type,
            local_dir=repo_dir,
            token=token,
            endpoint=endpoint,
        )
    except Exception as exc:
        _abort_download(pipe, f"ModelScope download failed: {exc}")


def unified_download_model(
    platform: str,
    model_id: str,
    save_path: str,
    token: str | None = None,
    endpoint: str | None = None,
    pipe=None,
    repo_type: str = "model",
):
    old_stdout, old_stderr = sys.stdout, sys.stderr
    if pipe is not None:
        sys.stdout = sys.stderr = pipe
    try:
        if platform == "huggingface":
            return download_huggingface(
                model_id, save_path, token, endpoint, pipe, repo_type
            )
        if platform == "modelscope":
            return download_modelscope(
                model_id, save_path, token, endpoint, pipe, repo_type
            )
        _abort_download(pipe, f"Unsupported platform '{platform}'")
    except Exception as exc:
        _abort_download(pipe, f"Error during {platform} download: {exc}")
    finally:
        if pipe is not None:
            pipe.flush()
            sys.stdout, sys.stderr = old_stdout, old_stderr
            pipe.send("DOWNLOAD_COMPLETE")


class UnifiedDownloadWorker(QThread):
    succeeded = pyqtSignal()
    stopped = pyqtSignal()
    error = pyqtSignal(str)
    status = pyqtSignal(str)
    log = pyqtSignal(str)

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
        if platform not in ("huggingface", "modelscope"):
            raise ValueError(f"Unsupported platform '{platform}'")
        self.platform = platform
        self.model_id = model_id
        self.save_path = save_path
        self.token = token
        self.repo_type = repo_type
        self.endpoint = (
            resolve_hf_endpoint(endpoint)
            if platform == "huggingface"
            else endpoint or "https://modelscope.cn"
        )
        self.repo_dir = os.path.join(save_path, model_id.split("/")[-1])
        self._cancel_event = threading.Event()

    @staticmethod
    def _isolated_download_wrapper(
        platform, model_id, save_path, token, endpoint, pipe, repo_type
    ):
        safe_pipe = SafePipeWriter(pipe)
        try:
            unified_download_model(
                platform, model_id, save_path, token, endpoint, safe_pipe, repo_type
            )
        except Exception as exc:
            safe_pipe.send(("error", f"Process wrapper error: {exc}"))
            raise SystemExit(1) from exc
        finally:
            pipe.close()

    def cancel_download(self):
        self._cancel_event.set()

    def run(self):
        reader = writer = process = None
        error_message = None
        try:
            if self._cancel_event.is_set():
                self.stopped.emit()
                return
            self.status.emit(
                f"Downloading {self.platform} {self.repo_type} to {self.repo_dir}..."
            )
            context = multiprocessing.get_context("spawn")
            reader, writer = context.Pipe(duplex=False)
            process = context.Process(
                target=self._isolated_download_wrapper,
                args=(
                    self.platform,
                    self.model_id,
                    self.save_path,
                    self.token,
                    self.endpoint,
                    writer,
                    self.repo_type,
                ),
            )
            if self._cancel_event.is_set():
                self.stopped.emit()
                return
            process.start()
            writer.close()
            pipe_open = True
            while process.is_alive() or pipe_open:
                if self._cancel_event.is_set() and process.is_alive():
                    process.terminate()
                    process.join(timeout=0.5)
                    if process.is_alive():
                        process.kill()
                        process.join()
                if pipe_open:
                    try:
                        if reader.poll(0.05):
                            output = reader.recv()
                            if output == "DOWNLOAD_COMPLETE":
                                pipe_open = False
                            elif isinstance(output, tuple) and output[0] == "error":
                                error_message = output[1]
                            else:
                                self.log.emit(str(output))
                    except (EOFError, OSError):
                        pipe_open = False
                else:
                    process.join(timeout=0.05)
            process.join()
            if self._cancel_event.is_set():
                self.stopped.emit()
            elif process.exitcode == 0:
                self.log.emit(
                    f"{self.platform} {self.repo_type.title()} downloaded to: "
                    f"{self.repo_dir}"
                )
                self.succeeded.emit()
            else:
                self.error.emit(
                    error_message
                    or f"{self.platform} download process failed "
                    f"(exit {process.exitcode})"
                )
        except Exception as exc:
            if self._cancel_event.is_set():
                self.stopped.emit()
            else:
                self.error.emit(str(exc))
        finally:
            if process is not None and process.pid is not None:
                if process.is_alive():
                    process.kill()
                process.join()
                process.close()
            for connection in (reader, writer):
                if connection is not None:
                    connection.close()
            cleanup_lock_files(self.repo_dir)
