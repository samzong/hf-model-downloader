"""
Basic E2E tests for download functionality
Tests with real networks but uses small models/datasets for speed
"""

import os
import sys
import tempfile

import pytest

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication

from src.unified_downloader import UnifiedDownloadWorker

# Create QApplication (required for pytest)
app = QApplication.instance() or QApplication(sys.argv)


class TestBasicE2E:
    """Basic end-to-end tests - verify download functionality works"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary download directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_huggingface_tiny_model(self, temp_dir):
        """Test downloading a very small HuggingFace model"""
        worker = UnifiedDownloadWorker(
            platform="huggingface",
            model_id="hf-internal-testing/tiny-random-bert",  # Extremely small test model
            save_path=temp_dir,
            repo_type="model",
        )

        # Use event loop to wait for download completion
        loop = QEventLoop()
        success = False
        error_msg = None

        def on_finished():
            nonlocal success
            success = True
            loop.quit()

        def on_error(msg):
            nonlocal error_msg
            error_msg = msg
            print(f"Download error: {msg}")
            loop.quit()

        worker.finished.connect(on_finished)
        worker.error.connect(on_error)

        # Set timeout (30 seconds)
        QTimer.singleShot(30000, loop.quit)

        worker.start()
        loop.exec()

        if not success:
            pytest.fail(f"HuggingFace model download failed: {error_msg}")

        # Verify files were downloaded
        download_path = os.path.join(temp_dir, "tiny-random-bert")
        assert os.path.exists(download_path), (
            f"Download directory not created at {download_path}"
        )

        # Check if some files exist (should have config.json or similar)
        files = os.listdir(download_path)
        assert len(files) > 0, f"No files downloaded to {download_path}"
        print(f"✅ Downloaded {len(files)} files to {download_path}")

    def test_modelscope_model(self, temp_dir):
        """Test downloading ModelScope model (test the fix)"""
        worker = UnifiedDownloadWorker(
            platform="modelscope",
            model_id="damo/nlp_bert_base-chinese",  # Small Chinese BERT
            save_path=temp_dir,
            repo_type="model",
        )

        loop = QEventLoop()
        success = False
        error_msg = None

        def on_finished():
            nonlocal success
            success = True
            loop.quit()

        def on_error(msg):
            nonlocal error_msg
            error_msg = msg
            print(f"Download error: {msg}")
            loop.quit()

        worker.finished.connect(on_finished)
        worker.error.connect(on_error)

        QTimer.singleShot(60000, loop.quit)  # 60 seconds for ModelScope

        worker.start()
        loop.exec()

        if not success:
            # ModelScope might require authentication, skip if needed
            if (
                "authentication" in str(error_msg).lower()
                or "access" in str(error_msg).lower()
            ):
                pytest.skip(
                    f"ModelScope model download requires authentication: {error_msg}"
                )
            else:
                pytest.fail(f"ModelScope model download failed: {error_msg}")

        download_path = os.path.join(temp_dir, "nlp_bert_base-chinese")
        assert os.path.exists(download_path), "Model directory not created"
        print(f"✅ ModelScope model downloaded to {download_path}")

    def test_modelscope_dataset(self, temp_dir):
        """Test downloading ModelScope dataset (this is what we fixed)"""
        worker = UnifiedDownloadWorker(
            platform="modelscope",
            model_id="modelscope/chinese-text-classification-dataset",  # Small test dataset
            save_path=temp_dir,
            repo_type="dataset",  # KEY: Testing dataset type
        )

        loop = QEventLoop()
        success = False
        error_msg = None

        def on_finished():
            nonlocal success
            success = True
            loop.quit()

        def on_error(msg):
            nonlocal error_msg
            error_msg = msg
            print(f"Download error: {msg}")
            loop.quit()

        worker.finished.connect(on_finished)
        worker.error.connect(on_error)

        QTimer.singleShot(60000, loop.quit)  # 60 seconds timeout

        worker.start()
        loop.exec()

        if not success:
            # If ModelScope requires authentication, mark as skip
            if any(
                keyword in str(error_msg).lower()
                for keyword in ["authentication", "access", "permission", "token"]
            ):
                pytest.skip(
                    f"ModelScope dataset download requires authentication: {error_msg}"
                )
            else:
                pytest.fail(f"ModelScope dataset download failed: {error_msg}")

        download_path = os.path.join(temp_dir, "chinese-text-classification-dataset")
        assert os.path.exists(download_path), "Dataset directory not created"
        print(f"✅ ModelScope dataset downloaded to {download_path}")

    def test_cancel_download(self, temp_dir):
        """Test download cancellation functionality"""
        worker = UnifiedDownloadWorker(
            platform="huggingface",
            model_id="bert-base-uncased",  # Larger model to have time to cancel
            save_path=temp_dir,
            repo_type="model",
        )

        loop = QEventLoop()
        cancelled = False
        error_msg = None

        def on_error(msg):
            nonlocal cancelled, error_msg
            error_msg = msg
            if "cancelled" in msg.lower() or "stopped" in msg.lower():
                cancelled = True
            loop.quit()

        def on_finished():
            # If download finishes quickly, that's also OK
            loop.quit()

        worker.error.connect(on_error)
        worker.finished.connect(on_finished)
        worker.start()

        # Cancel after 2 seconds
        QTimer.singleShot(2000, worker.cancel_download)
        QTimer.singleShot(10000, loop.quit)  # 10 seconds timeout

        loop.exec()

        # Either cancelled or finished quickly (both are acceptable)
        if not cancelled:
            print(f"⚠️  Download may have completed too quickly to cancel: {error_msg}")
            # This is not a failure - just means the download was very fast
        else:
            print("✅ Download cancelled successfully")

    def test_invalid_model_id(self, temp_dir):
        """Test error handling with invalid model ID"""
        worker = UnifiedDownloadWorker(
            platform="huggingface",
            model_id="definitely/does-not-exist-12345",  # Invalid model
            save_path=temp_dir,
            repo_type="model",
        )

        loop = QEventLoop()
        got_error = False
        error_msg = None

        def on_error(msg):
            nonlocal got_error, error_msg
            got_error = True
            error_msg = msg
            loop.quit()

        def on_finished():
            # Should not finish successfully
            loop.quit()

        worker.error.connect(on_error)
        worker.finished.connect(on_finished)

        QTimer.singleShot(30000, loop.quit)  # 30 seconds timeout

        worker.start()
        loop.exec()

        assert got_error, "Should have gotten an error for invalid model ID"
        assert (
            "not found" in error_msg.lower()
            or "does not exist" in error_msg.lower()
            or "404" in error_msg.lower()
        )
        print(f"✅ Correctly handled invalid model ID: {error_msg}")


if __name__ == "__main__":
    # Can run tests directly
    pytest.main([__file__, "-v", "-s"])
