# Makefile for HF Model Downloader

# 变量定义
PYTHON := python
PIP := pip
APP_NAME := hf-model-downloader
DIST_DIR := dist
BUILD_DIR := build
ASSETS_DIR := assets
ARCH := $(shell $(PYTHON) -c "import platform; print(platform.machine().lower())")

# Homebrew 相关变量
HOMEBREW_TAP_REPO = homebrew-tap
CASK_FILE = Casks/hf-model-downloader.rb
BRANCH_NAME = update-hf-model-downloader-$(shell echo $(VERSION) | sed 's/v//')
CLEAN_VERSION = $(shell echo $(VERSION) | sed 's/v//')

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
	@echo "  clean        - 清理构建目录"
	@echo "  build        - 构建应用"
	@echo "  dmg          - 创建 DMG 包"
	@echo "  help         - 显示此帮助信息"
	@echo ""
	@echo "当前架构: $(ARCH_NAME)" 

.DEFAULT_GOAL := help

# 更新 Homebrew Cask
.PHONY: update-homebrew
update-homebrew: ## 更新 Homebrew Cask (需要设置 GH_PAT 环境变量)
	@echo "$(BLUE)开始 Homebrew cask 更新流程...$(RESET)"
	@if [ -z "$(GH_PAT)" ]; then \
		echo "$(RED)错误: 需要设置 GH_PAT 环境变量$(RESET)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)当前版本信息:$(RESET)"
	@echo "    - VERSION: $(VERSION)"
	@echo "    - CLEAN_VERSION: $(CLEAN_VERSION)"

	@echo "$(BLUE)准备工作目录...$(RESET)"
	@rm -rf tmp && mkdir -p tmp
	
	@echo "$(BLUE)下载 DMG 文件...$(RESET)"
	@curl -L -o tmp/hf-model-downloader-arm64.dmg "https://github.com/samzong/hf-model-downloader/releases/download/v$(CLEAN_VERSION)/hf-model-downloader-arm64.dmg"
	@curl -L -o tmp/hf-model-downloader-x86_64.dmg "https://github.com/samzong/hf-model-downloader/releases/download/v$(CLEAN_VERSION)/hf-model-downloader-x86_64.dmg"

	@echo "$(BLUE)计算 SHA256 校验和...$(RESET)"
	@ARM64_SHA256=$$(shasum -a 256 tmp/hf-model-downloader-arm64.dmg | cut -d ' ' -f 1) && echo "    - ARM64 SHA256: $$ARM64_SHA256"
	@X86_64_SHA256=$$(shasum -a 256 tmp/hf-model-downloader-x86_64.dmg | cut -d ' ' -f 1) && echo "    - x86_64 SHA256: $$X86_64_SHA256"

	@echo "$(BLUE)克隆 Homebrew tap 仓库...$(RESET)"
	@cd tmp && git clone https://$(GH_PAT)@github.com/samzong/$(HOMEBREW_TAP_REPO).git
	@cd tmp/$(HOMEBREW_TAP_REPO) && echo "    - 创建新分支: $(BRANCH_NAME)" && git checkout -b $(BRANCH_NAME)

	@echo "$(BLUE)更新 cask 文件...$(RESET)"
	@ARM64_SHA256=$$(shasum -a 256 tmp/hf-model-downloader-arm64.dmg | cut -d ' ' -f 1) && \
	X86_64_SHA256=$$(shasum -a 256 tmp/hf-model-downloader-x86_64.dmg | cut -d ' ' -f 1) && \
	echo "$(BLUE)再次确认SHA256: ARM64=$$ARM64_SHA256, x86_64=$$X86_64_SHA256$(RESET)" && \
	cd tmp/$(HOMEBREW_TAP_REPO) && \
	echo "$(BLUE)当前目录: $$(pwd)$(RESET)" && \
	echo "$(BLUE)CASK_FILE路径: $(CASK_FILE)$(RESET)" && \
	if [ -f $(CASK_FILE) ]; then \
		echo "$(BLUE)发现现有cask文件，使用sed更新...$(RESET)"; \
		echo "$(BLUE)cask文件内容 (更新前):$(RESET)"; \
		cat $(CASK_FILE); \
		echo "$(BLUE)更新版本号...$(RESET)"; \
		sed -i '' "s/version \".*\"/version \"$(CLEAN_VERSION)\"/g" $(CASK_FILE); \
		echo "$(BLUE)更新版本号后的cask文件内容:$(RESET)"; \
		cat $(CASK_FILE); \
		if grep -q "Hardware::CPU.arm" $(CASK_FILE); then \
			echo "$(BLUE)更新ARM架构SHA256...$(RESET)"; \
			ARM_LINE_NUM=$$(grep -n "if Hardware::CPU.arm" $(CASK_FILE) | cut -d: -f1); \
			ARM_SHA_LINE_NUM=$$(tail -n +$$ARM_LINE_NUM $(CASK_FILE) | grep -n "sha256" | head -1 | cut -d: -f1); \
			ARM_SHA_LINE_NUM=$$((ARM_LINE_NUM + ARM_SHA_LINE_NUM - 1)); \
			sed -i '' "$${ARM_SHA_LINE_NUM}s/sha256 \".*\"/sha256 \"$$ARM64_SHA256\"/" $(CASK_FILE); \
			echo "$(BLUE)ARM SHA256 已更新在第 $$ARM_SHA_LINE_NUM 行$(RESET)"; \
			echo "$(BLUE)中间状态检查:$(RESET)"; \
			cat $(CASK_FILE); \
			echo "$(BLUE)更新Intel架构SHA256...$(RESET)"; \
			ELSE_LINE_NUM=$$(grep -n "else" $(CASK_FILE) | cut -d: -f1); \
			INTEL_SHA_LINE_NUM=$$(tail -n +$$ELSE_LINE_NUM $(CASK_FILE) | grep -n "sha256" | head -1 | cut -d: -f1); \
			INTEL_SHA_LINE_NUM=$$((ELSE_LINE_NUM + INTEL_SHA_LINE_NUM - 1)); \
			sed -i '' "$${INTEL_SHA_LINE_NUM}s/sha256 \".*\"/sha256 \"$$X86_64_SHA256\"/" $(CASK_FILE); \
			echo "$(BLUE)Intel SHA256 已更新在第 $$INTEL_SHA_LINE_NUM 行$(RESET)"; \
			echo "$(BLUE)最终cask文件内容:$(RESET)"; \
			cat $(CASK_FILE); \
		else \
			echo "$(RED)未找到 cask 格式，无法更新 SHA256 值$(RESET)"; \
			exit 1; \
		fi; \
	else \
		echo "$(RED)未找到cask文件: $(CASK_FILE)$(RESET)"; \
		exit 1; \
	fi

	@echo "$(BLUE)检查更改...$(RESET)"
	@cd tmp/$(HOMEBREW_TAP_REPO) && \
	if ! git diff --quiet $(CASK_FILE); then \
		echo "    - 检测到更改，创建 pull request..."; \
		git add $(CASK_FILE); \
		git config user.name "GitHub Actions"; \
		git config user.email "actions@github.com"; \
		git commit -m "chore: update hf-model-downloader to v$(CLEAN_VERSION)"; \
		git push -u origin $(BRANCH_NAME); \
		echo "    - 准备创建PR数据..."; \
		pr_data=$$(printf '{"title":"chore: update %s to v%s","body":"Auto-generated PR\\n\\n- Version: %s\\n- ARM64 SHA256: %s\\n- x86_64 SHA256: %s","head":"%s","base":"main"}' \
			"hf-model-downloader" "$(CLEAN_VERSION)" "$(CLEAN_VERSION)" "$$ARM64_SHA256" "$$X86_64_SHA256" "$(BRANCH_NAME)"); \
		echo "    - PR数据: $$pr_data"; \
		curl -X POST \
			-H "Authorization: token $(GH_PAT)" \
			-H "Content-Type: application/json" \
			https://api.github.com/repos/samzong/$(HOMEBREW_TAP_REPO)/pulls \
			-d "$$pr_data"; \
		echo "$(GREEN)✅ Pull request 创建成功$(RESET)"; \
	else \
		echo "$(RED)cask 文件中没有检测到更改$(RESET)"; \
		exit 1; \
	fi

	@echo "$(BLUE)清理临时文件...$(RESET)"
	@rm -rf tmp
	@echo "$(GREEN)✅ Homebrew cask 更新流程完成$(RESET)"
