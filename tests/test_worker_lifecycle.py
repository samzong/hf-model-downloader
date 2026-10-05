import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from PyQt6.QtCore import QEventLoop, QTimer

from src.ui import MainWindow
from src.unified_downloader import UnifiedDownloadWorker


@pytest.fixture
def hub_server():
    release = threading.Event()
    requested = threading.Event()
    state = {"mode": "stall"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            requested.set()
            if state["mode"] == "stall":
                release.wait(10)
                return
            if state["mode"] == "mismatch" and self.path.startswith("/api/datasets/"):
                self.send_response(200)
                body = json.dumps({"id": "org/model", "sha": "abc", "siblings": []})
            else:
                self.send_response(404)
                self.send_header("X-Error-Code", "RepoNotFound")
                body = "Repository not found"
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body.encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requested, state
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join()


def run_worker(worker, qt_app, action=None, timeout_ms=5000):
    result = {"success": False, "stopped": False, "errors": [], "logs": []}
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    worker.succeeded.connect(lambda: result.update(success=True))
    worker.stopped.connect(lambda: result.update(stopped=True))
    worker.error.connect(result["errors"].append)
    worker.log.connect(result["logs"].append)
    worker.finished.connect(loop.quit)
    worker.start()
    poll = QTimer()
    if action is not None:
        poll.timeout.connect(action)
        poll.start(10)
    timer.start(timeout_ms)
    try:
        loop.exec()
        assert worker.wait(100), "Worker did not finish before the deadline"
        qt_app.processEvents()
        return result
    finally:
        timer.stop()
        poll.stop()
        worker.cancel_download()
        assert worker.wait(3000)


def test_stop_interrupts_stalled_validation(qt_app, tmp_path, hub_server):
    endpoint, requested, _ = hub_server
    worker = UnifiedDownloadWorker(
        "huggingface", "org/model", str(tmp_path), endpoint=endpoint
    )
    stopped_at = []

    def stop_when_connected():
        if requested.is_set() and not stopped_at:
            stopped_at.append(time.monotonic())
            worker.cancel_download()

    result = run_worker(worker, qt_app, stop_when_connected)
    assert stopped_at
    assert time.monotonic() - stopped_at[0] < 3
    assert result["stopped"]
    assert not result["success"]
    assert not result["errors"]


def test_cancel_before_start_does_not_spawn(qt_app, tmp_path, monkeypatch):
    worker = UnifiedDownloadWorker("huggingface", "org/model", str(tmp_path))
    worker.cancel_download()

    def unexpected_spawn(*args):
        pytest.fail("Cancelled worker created a subprocess")

    monkeypatch.setattr(
        "src.unified_downloader.multiprocessing.get_context", unexpected_spawn
    )
    result = run_worker(worker, qt_app)
    assert result["stopped"]
    assert not result["success"]


def test_real_error_survives_child_exit(qt_app, tmp_path, hub_server):
    endpoint, _, state = hub_server
    state["mode"] = "missing"
    worker = UnifiedDownloadWorker(
        "huggingface", "org/model", str(tmp_path), endpoint=endpoint
    )
    result = run_worker(worker, qt_app)
    assert len(result["errors"]) == 1
    assert "Repository Not Found" in result["errors"][0]
    assert "cancelled" not in result["errors"][0]
    assert not result["success"]
    assert not result["stopped"]
    assert not any("Error:" in line for line in result["logs"])


def test_wrong_repo_type_hint_reaches_ui(qt_app, tmp_path, hub_server):
    endpoint, _, state = hub_server
    state["mode"] = "mismatch"
    window = MainWindow()
    window.repo_input.setText("org/model")
    window.path_input.setText(str(tmp_path))
    window.endpoint_input.setText(endpoint)
    window.start_download()
    worker = window.download_worker
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    worker.finished.connect(loop.quit)
    timer.start(5000)
    try:
        loop.exec()
        if window.download_worker is not None:
            assert worker.wait(100)
        qt_app.processEvents()
        text = window.log_text.toPlainText()
        assert text.count("This repository is a dataset, not a model.") == 1
        assert "Please switch the type to 'Dataset'" in text
        assert "❌ ❌" not in text
        assert window.download_worker is None
        assert window.download_button.isEnabled()
    finally:
        timer.stop()
        if window.download_worker is not None:
            worker.cancel_download()
            assert worker.wait(3000)
        window.close()


def test_ui_stop_waits_for_thread_finish(qt_app, tmp_path, hub_server):
    endpoint, requested, _ = hub_server
    window = MainWindow()
    window.repo_input.setText("org/model")
    window.path_input.setText(str(tmp_path))
    window.endpoint_input.setText(endpoint)
    window.start_download()
    worker = window.download_worker
    loop = QEventLoop()
    poll = QTimer()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    observed = []

    def stop_when_connected():
        if requested.is_set() and not observed:
            window.stop_download()
            observed.append(not window.download_button.isEnabled())
            assert window.download_worker is worker

    poll.timeout.connect(stop_when_connected)
    poll.start(10)
    worker.finished.connect(loop.quit)
    timer.start(5000)
    try:
        loop.exec()
        if window.download_worker is not None:
            assert worker.wait(100)
        qt_app.processEvents()
        assert observed == [True]
        assert window.log_text.toPlainText().count("Download stopped by user") == 1
        assert window.download_worker is None
        assert window.download_button.isEnabled()
    finally:
        timer.stop()
        poll.stop()
        if window.download_worker is not None:
            worker.cancel_download()
            assert worker.wait(3000)
        window.close()


def test_ui_success_waits_for_thread_finish(qt_app, tmp_path, monkeypatch):
    class LocalWorker(UnifiedDownloadWorker):
        def run(self):
            self.succeeded.emit()
            time.sleep(0.1)

    monkeypatch.setattr("src.ui.UnifiedDownloadWorker", LocalWorker)
    window = MainWindow()
    window.repo_input.setText("org/model")
    window.path_input.setText(str(tmp_path))
    window.start_download()
    worker = window.download_worker
    loop = QEventLoop()
    observed = []
    worker.succeeded.connect(
        lambda: observed.append(
            window.download_worker is worker and not window.download_button.isEnabled()
        )
    )
    worker.finished.connect(loop.quit)
    loop.exec()
    qt_app.processEvents()
    assert observed == [True]
    assert window.log_text.toPlainText().count("Download completed successfully!") == 1
    assert window.download_worker is None
    assert window.download_button.isEnabled()
    window.close()


def test_ui_close_cancels_without_terminating_qthread(qt_app, tmp_path, hub_server):
    endpoint, requested, _ = hub_server
    window = MainWindow()
    window.repo_input.setText("org/model")
    window.path_input.setText(str(tmp_path))
    window.endpoint_input.setText(endpoint)
    window.show()
    window.start_download()
    worker = window.download_worker
    loop = QEventLoop()
    poll = QTimer()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    closed = []

    def close_when_connected():
        if requested.is_set() and not closed:
            closed.append(window.close())
            assert window.download_worker is worker

    poll.timeout.connect(close_when_connected)
    poll.start(10)
    worker.finished.connect(loop.quit)
    timer.start(5000)
    try:
        loop.exec()
        if window.download_worker is not None:
            assert worker.wait(100)
        qt_app.processEvents()
        assert closed == [False]
        assert window.download_worker is None
        assert not window.isVisible()
    finally:
        timer.stop()
        poll.stop()
        if window.download_worker is not None:
            worker.cancel_download()
            assert worker.wait(3000)
        window.close()
