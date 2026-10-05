import multiprocessing
from unittest.mock import patch

import pytest

from src.unified_downloader import UnifiedDownloadWorker


def test_unsupported_platform_exits_nonzero():
    context = multiprocessing.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(
        target=UnifiedDownloadWorker._isolated_download_wrapper,
        args=("invalid-platform", "org/model", "/tmp", None, None, writer, "model"),
    )
    messages = []
    try:
        process.start()
        writer.close()
        while True:
            try:
                if not reader.poll(15):
                    break
                messages.append(reader.recv())
            except (EOFError, OSError):
                break
        process.join(timeout=15)
        assert process.exitcode not in (0, None)
        assert messages == [
            ("error", "Unsupported platform 'invalid-platform'"),
            "DOWNLOAD_COMPLETE",
        ]
    finally:
        if process.is_alive():
            process.kill()
            process.join()
        process.close()
        reader.close()
        writer.close()


def test_wrapper_exception_exits_nonzero():
    reader, writer = multiprocessing.Pipe(duplex=False)
    try:
        with patch(
            "src.unified_downloader.unified_download_model",
            side_effect=RuntimeError("wrapper failure"),
        ):
            with pytest.raises(SystemExit) as exc:
                UnifiedDownloadWorker._isolated_download_wrapper(
                    "huggingface", "org/model", "/tmp", None, None, writer, "model"
                )
        assert exc.value.code == 1
        assert reader.recv() == ("error", "Process wrapper error: wrapper failure")
    finally:
        reader.close()
        writer.close()
