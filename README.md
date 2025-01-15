# Hugging Face Model Downloader

A cross-platform GUI application for easily downloading Hugging Face models without requiring technical knowledge or setup.

![screenshot](./screenshot.png)

## Features

- Simple GUI interface for downloading Hugging Face models
- Support for custom Hugging Face tokens
- Custom endpoint/proxy support
- Download progress tracking
- Cross-platform support (Windows, macOS, Linux)
- No Python environment setup required

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/samzong/model-downloader.git
cd model-downloader
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## Building from Source

To create standalone executables:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

## License

MIT License 