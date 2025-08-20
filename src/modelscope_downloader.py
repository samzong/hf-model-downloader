"""
Backward compatibility wrapper for the original ModelScopeDownloadWorker
This file is DEPRECATED. Please use UnifiedDownloadWorker from unified_downloader.py instead.
"""

import warnings

from .unified_downloader import UnifiedDownloadWorker


class ModelScopeDownloadWorker(UnifiedDownloadWorker):
    """
    DEPRECATED: Backward compatibility wrapper for ModelScope downloads.
    Use UnifiedDownloadWorker('modelscope', ...) instead.
    """

    def __init__(
        self, model_id, save_path, token=None, endpoint=None, repo_type="model"
    ):
        warnings.warn(
            "ModelScopeDownloadWorker is deprecated. Use UnifiedDownloadWorker('modelscope', ...) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__("modelscope", model_id, save_path, token, endpoint, repo_type)


# For backward compatibility, also export the download function
def download_modelscope_model(
    model_id: str,
    save_path: str,
    token: str = None,
    endpoint: str = None,
    pipe=None,
    repo_type: str = "model",
):
    """
    DEPRECATED: Backward compatibility wrapper for ModelScope download function.
    Use unified_download_model('modelscope', ...) instead.
    """
    warnings.warn(
        "download_modelscope_model is deprecated. Use unified_download_model('modelscope', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from .unified_downloader import unified_download_model

    return unified_download_model(
        "modelscope", model_id, save_path, token, endpoint, pipe, repo_type
    )
