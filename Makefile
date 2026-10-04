# Makefile for HF Model Downloader

# === Configuration Variables ===
UV := uv
PYTHON := $(UV) run
APP_NAME := hf-model-downloader
ARCH_NAME := $(shell uname -m)
VERSION := $(shell grep '^version = ' pyproject.toml | cut -d'"' -f2)

# Build directories
DIST_DIR := dist

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
install: ## Install all dependencies with uv
	@command -v $(UV) >/dev/null 2>&1 || { echo "❌ uv is required. Install from https://docs.astral.sh/uv/" >&2; exit 1; }
	@echo "Installing Python dependencies with uv..."
	@$(UV) sync
	@echo "✅ Dependencies installed successfully"

.PHONY: format lint lint-fix test
format: install ## Apply code formatting fixes
	@echo "Applying code formatting fixes..."
	@$(UV) run ruff format .

lint: install ## Check code quality and style issues with ruff
	@echo "Running ruff code quality checks..."
	@$(UV) run ruff check .

lint-fix: install ## Auto-fix code issues where possible
	@echo "Auto-fixing code issues..."
	@$(UV) run ruff check --fix .
	@echo "✅ Auto-fixes applied"

test: install ## Run tests (fast smoke tests by default)
	@echo "Running tests..."
	@$(UV) run pytest tests/test_hf_xet.py tests/test_hf_hub_env.py tests/test_hf_repo_type.py tests/test_download_process.py -v

test-e2e: install ## Run full end-to-end download tests (network required)
	@echo "Running end-to-end tests..."
	@$(UV) run pytest tests/test_e2e_basic.py -v

.PHONY: check
check: format lint test build ## Run format, lint, smoke tests, and build

.PHONY: clean
clean: ## Clean build artifacts
	@echo "Cleaning build directories..."
	@rm -rf $(DIST_DIR) *.spec
	@echo "✅ Build artifacts cleaned"

.PHONY: dev
dev: install ## Run the application in development mode
	@echo "Starting application in development mode..."
	@$(PYTHON) main.py

##@ Build
.PHONY: build
build: install ## Build the application
	@echo "Building $(APP_NAME) v$(VERSION) for $(ARCH_NAME)..."
	@$(PYTHON) build.py
	@echo "✅ Build completed: $(DIST_DIR)"

.PHONY: dmg
dmg: install build ## Create DMG package (macOS only)
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
			$(UV) run dmgbuild -s settings.py "HF Model Downloader" "$(APP_NAME)-$(ARCH_NAME).dmg"; \
			break; \
		fi; \
	done
	@echo "✅ DMG created: $(DIST_DIR)/$(APP_NAME)-$(ARCH_NAME).dmg"

##@ Release
.PHONY: release-dry-run
release-dry-run: install ## Preview the next release version
	@$(UV) run semantic-release version --print

.DEFAULT_GOAL := help
