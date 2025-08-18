# Makefile for HF Model Downloader
# Optimized for maintainability and reliability

# === Configuration Variables ===
PYTHON := python
PIP := pip3
APP_NAME := hf-model-downloader

# Build directories
DIST_DIR := dist
BUILD_DIR := build
ASSETS_DIR := assets
SCRIPTS_DIR := scripts

# Platform detection
ARCH := $(shell $(PYTHON) -c "import platform; print(platform.machine().lower())")
ifeq ($(ARCH),arm64)
	ARCH_NAME := arm64
else ifeq ($(ARCH),x86_64)
	ARCH_NAME := x86_64
else
	ARCH_NAME := $(ARCH)
endif

# Version extraction (more robust)
VERSION := $(shell $(PYTHON) -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])" 2>/dev/null || \
           grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

# Semantic release configuration
CLEAN_VERSION := $(VERSION)
BRANCH_NAME := update-hf-model-downloader-$(VERSION)

# Color definitions for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
RESET := \033[0m

# === Utility Functions ===
define log_info
	echo "$(BLUE)$(1)$(RESET)"
endef

define log_success
	echo "$(GREEN)✅ $(1)$(RESET)"
endef

define log_warning
	echo "$(YELLOW)⚠️  $(1)$(RESET)"
endef

define log_error
	echo "$(RED)❌ $(1)$(RESET)" >&2
endef

# === Validation Functions ===
define check_python
	@which $(PYTHON) > /dev/null || ($(call log_error,Python not found); exit 1)
endef

define check_version
	@if [ -z "$(VERSION)" ]; then \
		$(call log_error,Could not extract version from pyproject.toml); \
		exit 1; \
	fi
endef

define check_build_deps
	$(call log_info,Checking build dependencies...)
	$(PYTHON) -c "import PyQt6" 2>/dev/null || ($(call log_error,PyQt6 not installed. Run 'make install' first); exit 1)
	$(PYTHON) -c "import pyinstaller" 2>/dev/null || ($(call log_error,PyInstaller not installed. Run 'make install' first); exit 1)
endef

# === Main Targets ===

.PHONY: help
help: ## Show this help message
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##";} /^[a-zA-Z_-]+:.*##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
	@echo "Current configuration:"
	@echo "  Platform: $(ARCH_NAME)"
	@echo "  Version:  $(VERSION)"
	@echo "  Python:   $(shell $(PYTHON) --version 2>/dev/null || echo 'Not found')"

.PHONY: version
version: ## Display current version information
	$(call check_version)
	$(call log_info,Current version: $(VERSION))

.PHONY: install
install: ## Install all dependencies
	$(call check_python)
	$(call log_info,Installing Python dependencies...)
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt
	@if command -v dmgbuild >/dev/null 2>&1; then \
		$(call log_success,dmgbuild already installed); \
	else \
		$(call log_info,Installing dmgbuild for DMG creation...); \
		$(PIP) install dmgbuild; \
	fi
	$(call log_success,Dependencies installed successfully)

.PHONY: clean
clean: ## Clean build artifacts
	$(call log_info,Cleaning build directories...)
	@rm -rf $(BUILD_DIR) $(DIST_DIR) *.spec
	$(call log_success,Build artifacts cleaned)

.PHONY: validate
validate: ## Validate project configuration
	$(call check_python)
	$(call check_version)
	$(call log_info,Validating project structure...)
	@test -f main.py || ($(call log_error,main.py not found); exit 1)
	@test -f build.py || ($(call log_error,build.py not found); exit 1)
	@test -f pyproject.toml || ($(call log_error,pyproject.toml not found); exit 1)
	@test -d src || ($(call log_error,src directory not found); exit 1)
	$(call log_success,Project validation passed)

.PHONY: build
build: validate ## Build the application
	$(call check_build_deps)
	@$(call log_info,Building $(APP_NAME) v$(VERSION) for $(ARCH_NAME)...)
	@$(PYTHON) build.py
	@$(call log_success,Build completed: $(DIST_DIR))

.PHONY: dmg
dmg: build ## Create DMG package (macOS only)
	@if [ "$(shell uname)" != "Darwin" ]; then \
		$(call log_error,DMG creation is only supported on macOS); \
		exit 1; \
	fi
	$(call log_info,Creating DMG package...)
	@if [ ! -d "$(DIST_DIR)" ]; then \
		$(call log_error,Dist directory not found. Run 'make build' first); \
		exit 1; \
	fi
	@cd $(DIST_DIR) && \
	for app_dir in *.app; do \
		if [ -d "$$app_dir" ]; then \
			$(call log_info,Processing $$app_dir...); \
			mv "$$app_dir" "HF Model Downloader.app"; \
			cp ../dmg_settings.py settings.py; \
			dmgbuild -s settings.py "HF Model Downloader" "$(APP_NAME)-macos-$(ARCH_NAME).dmg"; \
			break; \
		fi; \
	done
	$(call log_success,DMG created: $(DIST_DIR)/$(APP_NAME)-macos-$(ARCH_NAME).dmg)

.PHONY: package
package: clean build dmg ## Complete build and packaging workflow
	$(call log_success,Packaging completed successfully)

# === Release Management ===

.PHONY: release-dry-run
release-dry-run: ## Preview the next release version
	$(call log_info,Previewing next release version...)
	@semantic-release version --print

.PHONY: release
release: ## Execute semantic release (main branch only)
	$(call log_info,Executing semantic release...)
	@if [ "$$(git branch --show-current)" != "main" ]; then \
		$(call log_error,Release can only be executed on main branch); \
		exit 1; \
	fi
	@semantic-release version
	@semantic-release publish

# === Homebrew Integration ===

.PHONY: update-homebrew
update-homebrew: ## Update Homebrew Cask (requires GH_PAT environment variable)
	$(call check_version)
	@if [ -z "$(GH_PAT)" ]; then \
		$(call log_error,GH_PAT environment variable is required); \
		exit 1; \
	fi
	@if [ ! -x "$(SCRIPTS_DIR)/homebrew-update.sh" ]; then \
		$(call log_error,Homebrew update script not found or not executable); \
		exit 1; \
	fi
	$(call log_info,Starting Homebrew cask update process...)
	@$(SCRIPTS_DIR)/homebrew-update.sh

# === Development Targets ===

.PHONY: dev-install
dev-install: install ## Install development dependencies
	$(call log_info,Installing development dependencies...)
	@$(PIP) install semantic-release

.PHONY: test-build
test-build: clean validate ## Test build without creating DMG
	$(call log_info,Testing build process...)
	@$(PYTHON) build.py
	@if [ -d "$(DIST_DIR)" ] && [ -n "$$(ls -A $(DIST_DIR) 2>/dev/null)" ]; then \
		$(call log_success,Test build successful); \
	else \
		$(call log_error,Test build failed - no output in dist directory); \
		exit 1; \
	fi

.PHONY: check-deps
check-deps: ## Check if all dependencies are installed
	$(call log_info,Checking dependencies...)
	@$(PYTHON) -c "import PyQt6; print('✅ PyQt6 OK')" 2>/dev/null || echo "❌ PyQt6 missing"
	@$(PYTHON) -c "import pyinstaller; print('✅ PyInstaller OK')" 2>/dev/null || echo "❌ PyInstaller missing"
	@$(PYTHON) -c "import huggingface_hub; print('✅ Hugging Face Hub OK')" 2>/dev/null || echo "❌ Hugging Face Hub missing"
	@command -v dmgbuild >/dev/null 2>&1 && echo "✅ dmgbuild OK" || echo "❌ dmgbuild missing"

# === Quality Assurance ===

.PHONY: verify-release
verify-release: ## Verify release artifacts exist
	$(call check_version)
	$(call log_info,Verifying release artifacts for v$(VERSION)...)
	@curl -I "https://github.com/samzong/hf-model-downloader/releases/download/v$(VERSION)/$(APP_NAME)-arm64.dmg" 2>/dev/null | head -1 | grep -q "200 OK" && \
		$(call log_success,ARM64 DMG exists) || $(call log_warning,ARM64 DMG not found)
	@curl -I "https://github.com/samzong/hf-model-downloader/releases/download/v$(VERSION)/$(APP_NAME)-x86_64.dmg" 2>/dev/null | head -1 | grep -q "200 OK" && \
		$(call log_success,x86_64 DMG exists) || $(call log_warning,x86_64 DMG not found)

# === Meta Targets ===

.DEFAULT_GOAL := help

# Common dependency chains
build: | validate
dmg: | build  
package: | clean
release: | validate