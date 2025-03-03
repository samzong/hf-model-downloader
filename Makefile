# Makefile for HF Model Downloader

# 变量定义
PYTHON := python
PIP := pip
APP_NAME := hf-model-downloader
DIST_DIR := dist
BUILD_DIR := build
ASSETS_DIR := assets
ARCH := $(shell $(PYTHON) -c "import platform; print(platform.machine().lower())")

# 判断架构类型
ifeq ($(ARCH),arm64)
	ARCH_NAME := arm64
else ifeq ($(ARCH),x86_64)
	ARCH_NAME := x86_64
else
	ARCH_NAME := $(ARCH)
endif

# 安装依赖
.PHONY: install
install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install dmgbuild

# 生成图标
.PHONY: icons
icons:
	@echo "生成应用图标..."
	$(PYTHON) icon_generator.py --verbose --source $(ASSETS_DIR)/icon.png --output-dir $(ASSETS_DIR) --padding 15 --radius 22
	@echo "图标生成完成"

# 清理构建目录
.PHONY: clean
clean:
	rm -rf $(BUILD_DIR) $(DIST_DIR) *.spec

# 构建应用
.PHONY: build
build:
	$(PYTHON) build.py

# 创建 DMG 包
.PHONY: dmg
dmg:
	@echo "创建 DMG 包..."
	@cd $(DIST_DIR) && \
	for d in *.app; do \
		mv "$$d" "HF Model Downloader.app"; \
		cp ../dmg_settings.py settings.py; \
		dmgbuild -s settings.py "HF Model Downloader" "$(APP_NAME)-macos-$(ARCH_NAME).dmg"; \
	done
	@echo "DMG 创建完成: $(DIST_DIR)/$(APP_NAME)-macos-$(ARCH_NAME).dmg"

# 帮助信息
.PHONY: help
help:
	@echo "HF Model Downloader Makefile 帮助"
	@echo "可用目标:"
	@echo "  install      - 安装所需依赖"
	@echo "  icons        - 生成和修复应用图标"
	@echo "  clean        - 清理构建目录"
	@echo "  build        - 构建应用"
	@echo "  dmg          - 创建 DMG 包"
	@echo "  help         - 显示此帮助信息"
	@echo ""
	@echo "当前架构: $(ARCH_NAME)" 

.DEFAULT_GOAL := help