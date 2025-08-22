# hf-model-downloader

<div align="center">
  <img src="./assets/icon.png" alt="hf-model-downloader logo" width="200" />
  <br />
  <p>Downloads models from Hugging Face and ModelScope. Has a GUI so you don't need to mess with command lines.</p>
  <p>
    <a href="https://github.com/samzong/hf-model-downloader/releases"><img src="https://img.shields.io/github/v/release/samzong/hf-model-downloader" alt="Release Version" /></a>
    <a href="https://github.com/samzong/hf-model-downloader/blob/main/LICENSE"><img src="https://img.shields.io/github/license/samzong/hf-model-downloader" alt="MIT License" /></a>
    <a href="https://deepwiki.com/samzong//hf-model-downloader"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>
  </p>
</div>

![screenshot](./screenshot.png)

## What it does

- Downloads Hugging Face and ModelScope models through a simple GUI
- Handles authentication tokens
- Shows download progress
- Works on Windows, macOS, Linux
- Creates standalone apps you can just run

## Just want to use it?

Download from [releases](https://github.com/samzong/hf-model-downloader/releases). Run the app. Done.

## Development

```bash
git clone https://github.com/samzong/hf-model-downloader.git
cd hf-model-downloader

# Modern way (recommended)
uv sync
uv run main.py
```

## Build

```bash
# Build the application
make build

# Create DMG package (macOS only)
make dmg

# Clean build artifacts
make clean
```

## Code Quality

```bash
# Format code
make format

# Check code quality
make lint

# Auto-fix issues
make lint-fix

# Run format + lint + build
make check
```

## Release

```bash
# Preview next version
make release-dry-run

# Create release (main branch only)
make release
```

**See all available commands:**
```bash
make help
```

## License

Under the MIT License - see the [LICENSE](LICENSE).
