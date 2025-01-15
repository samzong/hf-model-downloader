"""
Utility functions for the Model Downloader
"""

import os
import logging

# Configure logging
logger = logging.getLogger("huggingface_hub")
logger.setLevel(logging.INFO)

def cleanup_lock_files(directory):
    """Clean up any .lock files in the directory and its subdirectories."""
    logger.info("Cleaning up lock files (keeping downloaded chunks for resume)...")
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.lock'):
                    lock_file = os.path.join(root, file)
                    try:
                        os.remove(lock_file)
                        logger.info(f"Removed lock file: {lock_file}")
                    except Exception as e:
                        logger.warning(f"Could not remove lock file {lock_file}: {str(e)}")
    except Exception as e:
        logger.warning(f"Error while cleaning lock files: {str(e)}")

def cleanup_environment():
    """Clean up environment variables."""
    # 只清理认证和 SSL 相关的环境变量，保留 endpoint 设置
    env_vars = ['HF_TOKEN', 'HF_HUB_DISABLE_SSL_VERIFICATION']
    for var in env_vars:
        if var in os.environ:
            del os.environ[var] 