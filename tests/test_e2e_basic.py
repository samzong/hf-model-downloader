from pathlib import Path

import pytest
from PyQt6.QtCore import QEventLoop, QTimer

from src.unified_downloader import UnifiedDownloadWorker

pytestmark = [pytest.mark.network, pytest.mark.slow]


def download(qt_app, tmp_path, platform, repo_id, repo_type="model", endpoint=None):
    worker = UnifiedDownloadWorker(
        platform, repo_id, str(tmp_path), endpoint=endpoint, repo_type=repo_type
    )
    result = {"success": False, "error": None}
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    worker.succeeded.connect(lambda: result.update(success=True))
    worker.error.connect(lambda message: result.update(error=message))
    worker.finished.connect(loop.quit)
    timer.start(180000)
    worker.start()
    try:
        loop.exec()
        assert worker.wait(100), "Download exceeded 180 seconds"
        qt_app.processEvents()
        return result
    finally:
        timer.stop()
        worker.cancel_download()
        assert worker.wait(3000)


class TestBasicE2E:
    def test_huggingface_tiny_model(self, qt_app, tmp_path):
        result = download(
            qt_app, tmp_path, "huggingface", "hf-internal-testing/tiny-random-bert"
        )
        assert result["success"], result["error"]
        repo = tmp_path / "tiny-random-bert"
        assert (repo / "config.json").is_file()
        assert (repo / "pytorch_model.bin").stat().st_size > 0
        assert (repo / ".gitattributes").is_file()
        assert (repo / "onnx" / "model.onnx").stat().st_size > 0

    def test_modelscope_model(self, qt_app, tmp_path):
        repo_id = "iic/nlp_structbert_sentence-similarity_chinese-tiny"
        result = download(qt_app, tmp_path, "modelscope", repo_id)
        assert result["success"], result["error"]
        repo = tmp_path / Path(repo_id).name
        assert (repo / "pytorch_model.bin").stat().st_size > 0
        assert (repo / ".gitattributes").is_file()

    def test_modelscope_dataset(self, qt_app, tmp_path):
        result = download(
            qt_app, tmp_path, "modelscope", "swift/self-cognition", "dataset"
        )
        assert result["success"], result["error"]
        repo = tmp_path / "self-cognition"
        assert (repo / "self_cognition.jsonl").stat().st_size > 0
        assert (repo / "dataset_infos.json").is_file()
        assert (repo / ".gitattributes").is_file()

    def test_invalid_model_id(self, qt_app, tmp_path):
        result = download(
            qt_app, tmp_path, "huggingface", "definitely/does-not-exist-12345"
        )
        assert not result["success"]
        assert result["error"]
        assert "cancelled" not in result["error"].lower()
        assert any(
            text in result["error"].lower()
            for text in ("not found", "does not exist", "404", "401")
        )

    def test_wrong_repo_type(self, qt_app, tmp_path):
        result = download(
            qt_app,
            tmp_path,
            "huggingface",
            "hf-internal-testing/tiny-random-bert",
            "dataset",
            "https://huggingface.co",
        )
        assert not result["success"]
        assert "is a model, not a dataset" in result["error"]
        assert "switch the type to 'Model'" in result["error"]
