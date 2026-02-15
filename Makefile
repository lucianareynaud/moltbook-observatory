# Moltbook Observatory — Makefile
# POSIX-compatible automation for common tasks

.POSIX:
.SUFFIXES:

PYTHON := python3
VENV := .venv
BIN := $(VENV)/bin
SHELL := /bin/sh

# Default target
.PHONY: help
help:
	@echo "Moltbook Observatory — Available targets:"
	@echo ""
	@echo "  Setup & Installation:"
	@echo "    make venv           Create Python virtual environment"
	@echo "    make install        Install dependencies"
	@echo "    make setup          Complete setup (venv + install)"
	@echo ""
	@echo "  Code Quality:"
	@echo "    make lint           Run code linters (ruff)"
	@echo "    make format         Format code (ruff format)"
	@echo "    make check          Run lint + format check"
	@echo ""
	@echo "  Data Collection:"
	@echo "    make collect        Run collector once"
	@echo ""
	@echo "  Reporting:"
	@echo "    make report         Generate weekly report (previous week)"
	@echo "    make report-current Generate report for current week"
	@echo ""
	@echo "  Cleanup:"
	@echo "    make clean          Remove generated files"
	@echo "    make clean-all      Remove venv + generated files"
	@echo ""

# Setup targets
.PHONY: venv
venv:
	@scripts/venv.sh

.PHONY: install
install:
	@scripts/install.sh

.PHONY: setup
setup: venv install
	@echo "[make] Setup complete"

# Code quality targets
.PHONY: lint
lint:
	@scripts/lint.sh

.PHONY: format
format:
	@scripts/format.sh

.PHONY: check
check: lint
	@scripts/format.sh --check

# Data collection targets
.PHONY: collect
collect:
	@scripts/collect.sh

# Reporting targets
.PHONY: report
report:
	@scripts/report.sh

.PHONY: report-current
report-current:
	@scripts/report.sh --current

# Cleanup targets
.PHONY: clean
clean:
	@echo "[make] Cleaning generated files..."
	@rm -rf output/*/
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "[make] Clean complete"

.PHONY: clean-all
clean-all: clean
	@echo "[make] Removing virtual environment..."
	@rm -rf $(VENV)
	@echo "[make] Clean all complete"
