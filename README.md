# hf-model-downloader

<div align="center">
  <img src="./assets/icon.png" alt="hf-model-downloader logo" width="200" />
  <br />
  
  <!-- 智能下载按钮 -->
  <div id="download-section" style="margin: 20px 0;">
    <a href="#" onclick="downloadLatest(); return false;" style="text-decoration: none;">
      <img src="https://img.shields.io/badge/⬇%20Download%20for%20Your%20System-28a745?style=for-the-badge&labelColor=28a745" alt="Download" />
    </a>
  </div>
  
  <script>
  function downloadLatest() {
    // 检测操作系统和架构
    const platform = navigator.platform.toLowerCase();
    const userAgent = navigator.userAgent.toLowerCase();
    
    let downloadUrl = '';
    
    if (platform.includes('mac')) {
      // macOS - 检测是否为 Apple Silicon
      if (userAgent.includes('arm') || userAgent.includes('apple')) {
        downloadUrl = 'https://github.com/samzong/hf-model-downloader/releases/latest/download/hf-model-downloader-macOS-arm64.dmg';
      } else {
        downloadUrl = 'https://github.com/samzong/hf-model-downloader/releases/latest/download/hf-model-downloader-macOS-x86_64.dmg';
      }
    } else if (platform.includes('win')) {
      // Windows - 预留
      alert('Windows version coming soon!');
      return;
    } else {
      // Linux 或其他 - 跳转到 releases 页面
      window.open('https://github.com/samzong/hf-model-downloader/releases/latest', '_blank');
      return;
    }
    
    // 直接触发下载
    window.location.href = downloadUrl;
  }
  </script>
  
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
