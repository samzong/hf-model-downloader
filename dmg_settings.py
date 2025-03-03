from dmgbuild import *

# DMG 格式设置
format = "UDBZ"

# 要包含的文件
files = ["HF Model Downloader.app"]

# 添加 Applications 文件夹的符号链接
symlinks = { "Applications": "/Applications" }

# 设置图标
badge_icon = "HF Model Downloader.app/Contents/Resources/icon-windowed.icns"

# 设置图标位置
icon_locations = {
    "HF Model Downloader.app": (140, 120),
    "Applications": (500, 120)
} 