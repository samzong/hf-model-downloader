# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the application
```bash
python main.py
```

### Installing dependencies
```bash
pip install -r requirements.txt
# or using Makefile
make install
```

### Building the application
```bash
# Build using Python script
python build.py

# Or using Makefile
make build

# Create DMG package (macOS only)
make dmg

# Clean build artifacts
make clean
```

### Building with PyInstaller directly
```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

## Architecture Overview

This is a PyQt6-based GUI application for downloading Hugging Face models. The architecture separates UI, download logic, and utilities into distinct modules.

### Key Components

- **main.py**: Entry point handling PyInstaller packaging, platform-specific icons, and application initialization
- **src/ui.py**: Main window with download form, progress display, and user guidance
- **src/downloader.py**: Core download functionality using huggingface_hub with multiprocessing support
- **src/utils.py**: Cleanup utilities for lock files and environment management
- **build.py**: PyInstaller build script with platform-specific configurations

### Multiprocessing Architecture

The downloader uses multiprocessing to prevent UI blocking:
- Download operations run in separate processes
- Progress updates sent via pipes to the main UI thread
- Special handling for PyInstaller frozen environments
- Platform-specific multiprocessing setup (spawn method on macOS)

### Platform-Specific Features

- Icons: .icns for macOS, .ico for Windows, .png for Linux
- Build outputs: DMG for macOS, executable for other platforms
- Architecture detection: arm64/x86_64 support with automatic detection
- UTF-8 encoding enforcement on Windows

### Build System

Uses both Makefile and Python script:
- **Makefile**: High-level tasks (install, build, dmg, clean)
- **build.py**: PyInstaller configuration with platform detection
- Automatic architecture detection and naming in output files