# Makefile for HF Model Downloader

# === Configuration Variables ===
UV := uv
PYTHON := $(shell if command -v uv >/dev/null 2>&1; then echo "uv run"; else echo "python"; fi)
APP_NAME := hf-model-downloader
ARCH_NAME := $(shell uname -m)
VERSION := $(shell grep '^version = ' pyproject.toml | cut -d'"' -f2)

# Build directories
DIST_DIR := dist
SCRIPTS_DIR := scripts

##@ Basic
.PHONY: help
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""
	@echo "Current:"
	@echo "  Platform: $(ARCH_NAME)"
	@echo "  Version:  $(VERSION)"
	@echo "  Python:   $(shell $(PYTHON) python --version 2>/dev/null || echo 'Not found')"

##@ Development
.PHONY: install
install: ## Install all dependencies
	@if command -v uv >/dev/null 2>&1; then \
		echo "Installing Python dependencies with uv..."; \
		$(UV) sync; \
	else \
		echo "uv not found, falling back to pip..."; \
		echo "Installing runtime dependencies..."; \
		pip install -r requirements.txt; \
		echo "Installing dev dependencies..."; \
		pip install -r requirements-dev.txt; \
	fi
	@echo "✅ Dependencies installed successfully"

.PHONY: format lint lint-fix
format: ## Apply code formatting fixes
	@echo "Applying code formatting fixes..."
	@ruff format .

lint: ## Check code quality and style issues with ruff
	@echo "Running ruff code quality checks..."
	@ruff check .

lint-fix: ## Auto-fix code issues where possible
	@echo "Auto-fixing code issues..."
	@ruff check --fix .
	@echo "✅ Auto-fixes applied"

.PHONY: check
check: format lint build ## auto run format,lint,build

.PHONY: clean
clean: ## Clean build artifacts
	@echo "Cleaning build directories..."
	@rm -rf $(DIST_DIR) *.spec
	@echo "✅ Build artifacts cleaned"

.PHONY: dev
dev: ## Run the application in development mode
	@echo "Starting application in development mode..."
	@$(PYTHON) main.py

##@ Build
.PHONY: build
build: ## Build the application
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

##@ Release
.PHONY: release-dry-run
release-dry-run: ## Preview the next release version
	@semantic-release version --print

.PHONY: release
release: ## Execute semantic release (main branch only)
	@if [ "$$(git branch --show-current)" != "main" ]; then \
		echo "❌ Release can only be executed on main branch" >&2; \
		exit 1; \
	fi
	@semantic-release version
	@semantic-release publish

.DEFAULT_GOAL := help

# Add CI-only targets for GitHub Actions (not in help)
.PHONY: update-homebrew verify-release
update-homebrew:
	@if [ -z "$(GH_PAT)" ]; then echo "❌ GH_PAT required" >&2; exit 1; fi
	@export VERSION="$(VERSION)"; $(SCRIPTS_DIR)/homebrew-update.sh

verify-release:
	@curl -I "https://github.com/samzong/hf-model-downloader/releases/download/v$(VERSION)/$(APP_NAME)-arm64.dmg" 2>/dev/null | head -1 | grep -q "200 OK" && echo "✅ ARM64 DMG exists" || echo "⚠️ ARM64 DMG not found"
	@curl -I "https://github.com/samzong/hf-model-downloader/releases/download/v$(VERSION)/$(APP_NAME)-x86_64.dmg" 2>/dev/null | head -1 | grep -q "200 OK" && echo "✅ x86_64 DMG exists" || echo "⚠️ x86_64 DMG not found"
