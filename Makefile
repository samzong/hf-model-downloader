# Makefile for HF Model Downloader

# === Configuration Variables ===
PYTHON := python
PIP := pip3
APP_NAME := hf-model-downloader
ARCH := $(shell uname -m)
VERSION := $(shell grep '^version = ' pyproject.toml | cut -d'"' -f2)

# Build directories
DIST_DIR := dist
SCRIPTS_DIR := scripts

# === Validation Functions ===
define check_python
	@which $(PYTHON) > /dev/null || (echo "❌ Python not found" >&2; exit 1)
endef

define check_version
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ Could not extract version from pyproject.toml" >&2; \
		exit 1; \
	fi
endef

define check_build_deps
	@echo "Checking build dependencies..."
	@$(PYTHON) -c "import PyQt6" 2>/dev/null || (echo "❌ PyQt6 not installed. Run 'make install' first" >&2; exit 1)
	@$(PYTHON) -c "import PyInstaller" 2>/dev/null || (echo "❌ PyInstaller not installed. Run 'make install' first" >&2; exit 1)
endef

##@ Basic
.PHONY: help
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""
	@echo "Current configuration:"
	@echo "  Platform: $(ARCH_NAME)"
	@echo "  Version:  $(VERSION)"
	@echo "  Python:   $(shell $(PYTHON) --version 2>/dev/null || echo 'Not found')"

.PHONY: version
version: ## Display current version information
	$(call check_version)
	@echo "Current version: $(VERSION)"

##@ Development
.PHONY: install
install: ## Install all dependencies
	$(call check_python)
	@echo "Installing Python dependencies..."
	@$(PIP) install -r requirements.txt --break-system-packages
	@if command -v dmgbuild >/dev/null 2>&1; then \
		echo "✅ dmgbuild already installed"; \
	else \
		echo "Installing dmgbuild for DMG creation..."; \
		$(PIP) install dmgbuild --break-system-packages; \
	fi
	@echo "✅ Dependencies installed successfully"

.PHONY: clean
clean: ## Clean build artifacts
	@echo "Cleaning build directories..."
	@rm -rf $(DIST_DIR) *.spec
	@echo "✅ Build artifacts cleaned"

.PHONY: dev dev-install
dev: ## Run the application in development mode
	$(call check_python)
	@echo "Starting application in development mode..."
	@$(PYTHON) main.py

dev-install: install ## Install development dependencies
	@echo "Installing development dependencies..."
	@$(PIP) install python-semantic-release --break-system-packages

.PHONY: test-build
test-build: clean validate ## Test the build process
	@echo "Testing build process..."
	@$(PYTHON) build.py
	@if [ -d "$(DIST_DIR)" ] && [ -n "$$(ls -A $(DIST_DIR) 2>/dev/null)" ]; then \
		echo "✅ Test build successful"; \
	else \
		echo "❌ Test build failed - no output in dist directory" >&2; \
		exit 1; \
	fi

.PHONY: check-deps
check-deps: ## Check dependencies
	@echo "Checking dependencies..."
	@$(PYTHON) -c "import PyQt6; print('✅ PyQt6 OK')" 2>/dev/null || echo "❌ PyQt6 missing"
	@$(PYTHON) -c "import PyInstaller; print('✅ PyInstaller OK')" 2>/dev/null || echo "❌ PyInstaller missing"
	@$(PYTHON) -c "import huggingface_hub; print('✅ Hugging Face Hub OK')" 2>/dev/null || echo "❌ Hugging Face Hub missing"
	@command -v dmgbuild >/dev/null 2>&1 && echo "✅ dmgbuild OK" || echo "❌ dmgbuild missing"

.PHONY: validate
validate: ## Validate project configuration
	$(call check_python)
	$(call check_version)
	@echo "Validating project structure..."
	@test -f main.py || (echo "❌ main.py not found" >&2; exit 1)
	@test -f build.py || (echo "❌ build.py not found" >&2; exit 1)
	@test -f pyproject.toml || (echo "❌ pyproject.toml not found" >&2; exit 1)
	@test -d src || (echo "❌ src directory not found" >&2; exit 1)
	@echo "✅ Project validation passed"

##@ Build
.PHONY: build
build: validate ## Build the application
	$(call check_build_deps)
	@echo "Building $(APP_NAME) v$(VERSION) for $(ARCH_NAME)..."
	@$(PYTHON) build.py
	@echo "✅ Build completed: $(DIST_DIR)"

.PHONY: dmg
dmg: build ## Create DMG package (macOS only)
	@if [ "$(shell uname)" != "Darwin" ]; then \
		echo "❌ DMG creation is only supported on macOS" >&2; \
		exit 1; \
	fi
	@echo "Creating DMG package..."
	@if [ ! -d "$(DIST_DIR)" ]; then \
		echo "❌ Dist directory not found. Run 'make build' first" >&2; \
		exit 1; \
	fi
	@cd $(DIST_DIR) && \
	for app_dir in *.app; do \
		if [ -d "$$app_dir" ]; then \
			echo "Processing $$app_dir..."; \
			mv "$$app_dir" "HF Model Downloader.app"; \
			cp ../dmg_settings.py settings.py; \
			dmgbuild -s settings.py "HF Model Downloader" "$(APP_NAME)-$(ARCH_NAME).dmg"; \
			break; \
		fi; \
	done
	@echo "✅ DMG created: $(DIST_DIR)/$(APP_NAME)-$(ARCH_NAME).dmg"

.PHONY: package
package: clean build dmg ## Complete build and packaging workflow
	@echo "✅ Packaging completed successfully"

##@ Release
.PHONY: release-dry-run
release-dry-run: ## Preview the next release version
	@echo "Previewing next release version..."
	@semantic-release version --print

.PHONY: release
release: ## Execute semantic release (main branch only)
	@echo "Executing semantic release..."
	@if [ "$$(git branch --show-current)" != "main" ]; then \
		echo "❌ Release can only be executed on main branch" >&2; \
		exit 1; \
	fi
	@semantic-release version
	@semantic-release publish

.PHONY: update-homebrew
update-homebrew: ## Update Homebrew Cask (requires GH_PAT environment variable)
	$(call check_version)
	@if [ -z "$(GH_PAT)" ]; then \
		echo "❌ GH_PAT environment variable is required" >&2; \
		exit 1; \
	fi
	@if [ ! -x "$(SCRIPTS_DIR)/homebrew-update.sh" ]; then \
		echo "❌ Homebrew update script not found or not executable" >&2; \
		exit 1; \
	fi
	@echo "Starting Homebrew cask update process..."
	@export VERSION="$(VERSION)"; $(SCRIPTS_DIR)/homebrew-update.sh

.PHONY: verify-release
verify-release: ## Verify release artifacts exist
	$(call check_version)
	@echo "Verifying release artifacts for v$(VERSION)..."
	@curl -I "https://github.com/samzong/hf-model-downloader/releases/download/v$(VERSION)/$(APP_NAME)-arm64.dmg" 2>/dev/null | head -1 | grep -q "200 OK" && \
		echo "✅ ARM64 DMG exists" || echo "⚠️ ARM64 DMG not found"
	@curl -I "https://github.com/samzong/hf-model-downloader/releases/download/v$(VERSION)/$(APP_NAME)-x86_64.dmg" 2>/dev/null | head -1 | grep -q "200 OK" && \
		echo "✅ x86_64 DMG exists" || echo "⚠️ x86_64 DMG not found"

.DEFAULT_GOAL := help

# Common dependency chains
build: | validate
dmg: | build  
package: | clean
release: | validate
