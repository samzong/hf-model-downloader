import logging
import os

logger = logging.getLogger(__name__)


def cleanup_lock_files(directory):
    for root, _dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".lock"):
                lock_file = os.path.join(root, file)
                try:
                    os.remove(lock_file)
                except OSError as exc:
                    logger.warning("Could not remove lock file %s: %s", lock_file, exc)
