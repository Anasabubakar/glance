# ────────────────────────────────────────────────────────────────────
# Glance — Cross-platform build system
# ────────────────────────────────────────────────────────────────────

VERSION := $(shell python3 -c "import glance; print(glance.__version__)" 2>/dev/null || echo "0.1.0")
ARCH := $(shell dpkg --print-architecture 2>/dev/null || echo "amd64")

.PHONY: help icons install-deps build build-linux appimage deb all-linux \
        build-windows clean test lint

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────────────

icons: ## Generate all platform icons from glance.png
	python3 packaging/generate_icons.py

install-deps: ## Install Python dependencies for building
	pip install -e ".[shell,claude,dev]"
	pip install pyinstaller

# ── Linux ─────────────────────────────────────────────────────────────

build-linux: ## Build portable Linux binary (dist/Glance/)
	chmod +x packaging/linux/build-linux.sh
	bash packaging/linux/build-linux.sh

appimage: ## Build Linux AppImage
	chmod +x packaging/linux/build-linux.sh
	bash packaging/linux/build-linux.sh appimage

deb: ## Build Linux .deb package
	chmod +x packaging/linux/build-linux.sh
	bash packaging/linux/build-linux.sh deb

all-linux: ## Build all Linux packages (portable + AppImage + .deb)
	chmod +x packaging/linux/build-linux.sh
	bash packaging/linux/build-linux.sh all

# ── Windows (run on Windows or via CI) ────────────────────────────────

build-windows: ## Build Windows .exe (run on Windows)
	@echo "Run on Windows:  build.bat"
	@echo "With installer:  build.bat installer"

# ── General ───────────────────────────────────────────────────────────

build: ## Build for current platform
ifeq ($(shell uname -s),Linux)
	$(MAKE) build-linux
else
	@echo "Run build.bat on Windows"
endif

clean: ## Remove build artifacts
	rm -rf build/ dist/
	rm -rf packaging/icons/

test: ## Run tests
	python3 -m pytest tests/ -v

lint: ## Run linters
	python3 -m flake8 glance/ --max-line-length=120 --ignore=E501,W503 || true
