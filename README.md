# hf-model-downloader

<div align="center">
  <img src="./assets/icon.png" alt="hf-model-downloader logo" width="200" />
  <br />
  <p>A cross-platform GUI application for easily downloading Hugging Face models without requiring technical knowledge or setup.</p>
  <p>
    <a href="https://github.com/samzong/hf-model-downloader/releases"><img src="https://img.shields.io/github/v/release/samzong/hf-model-downloader" alt="Release Version" /></a>
    <a href="https://github.com/samzong/hf-model-downloader/blob/main/LICENSE"><img src="https://img.shields.io/github/license/samzong/hf-model-downloader" alt="MIT License" /></a>
  </p>
</div>

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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
