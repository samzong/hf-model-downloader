"""
Backward compatibility wrapper for the original DownloadWorker
This file is DEPRECATED. Please use UnifiedDownloadWorker from unified_downloader.py
"""

import warnings

from .unified_downloader import UnifiedDownloadWorker


class DownloadWorker(UnifiedDownloadWorker):
    """
    DEPRECATED: Backward compatibility wrapper for HuggingFace downloads.
    Use UnifiedDownloadWorker('huggingface', ...) instead.
    """

    def __init__(
        self, model_id, save_path, token=None, endpoint=None, repo_type="model"
    ):
        warnings.warn(
            "DownloadWorker is deprecated. Use UnifiedDownloadWorker",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__("huggingface", model_id, save_path, token, endpoint, repo_type)


# For backward compatibility, also export the download function
def download_model(
    model_id: str,
    save_path: str,
    token: str = None,
    endpoint: str = None,
    pipe=None,
    repo_type: str = "model",
):
    """
    DEPRECATED: Backward compatibility wrapper for HuggingFace download function.
    Use unified_download_model('huggingface', ...) instead.
    """
    warnings.warn(
        "download_model is deprecated. Use unified_download_model.",
        DeprecationWarning,
        stacklevel=2,
    )
    from .unified_downloader import unified_download_model

    return unified_download_model(
        "huggingface", model_id, save_path, token, endpoint, pipe, repo_type
    )
