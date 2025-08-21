"""
Resource path utilities for handling assets in both development and packaged environments
"""

import os
import sys


def get_resource_path(relative_path):
    """
    Get the absolute path to a resource file.
    
    Works in both development environment and PyInstaller packaged environment.
    
    Args:
        relative_path (str): Path relative to the application root (e.g., "assets/icon.png")
        
    Returns:
        str: Absolute path to the resource file
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # This is the path where PyInstaller extracts bundled files
        base_path = sys._MEIPASS
    except AttributeError:
        # Running in development environment
        # Get the parent directory of this file (go up from src/ to project root)
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)


def get_asset_path(filename):
    """
    Get the absolute path to an asset file in the assets directory.
    
    Args:
        filename (str): Asset filename (e.g., "icon.png", "huggingface_logo.png")
        
    Returns:
        str: Absolute path to the asset file
    """
    return get_resource_path(os.path.join("assets", filename))
