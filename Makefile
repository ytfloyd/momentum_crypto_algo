# Coinbase Rebalance Agent Makefile

# Variables
PYTHON := python3.12
VENV_DIR := .venv
VENV_ACTIVATE := $(VENV_DIR)/bin/activate
PIP := $(VENV_DIR)/bin/pip
PYTHON_VENV := $(VENV_DIR)/bin/python

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

.PHONY: help venv install test clean format lint run notebook deploy status

# Default target
help:
	@echo "$(BLUE)Coinbase Rebalance Agent$(NC)"
	@echo "Available commands:"
	@echo "  $(GREEN)make venv$(NC)     - Create virtual environment and install dependencies"
	@echo "  $(GREEN)make install$(NC)  - Install dependencies in existing venv"
	@echo "  $(GREEN)make test$(NC)     - Run tests"
	@echo "  $(GREEN)make format$(NC)   - Format code with black and isort"
	@echo "  $(GREEN)make lint$(NC)     - Run linting checks"
	@echo "  $(GREEN)make run$(NC)      - Start the rebalancing agent"
	@echo "  $(GREEN)make notebook$(NC) - Launch Jupyter Lab"
	@echo "  $(GREEN)make deploy$(NC)   - Deploy to production (git push)"
	@echo "  $(GREEN)make status$(NC)   - Show project status"
	@echo "  $(GREEN)make clean$(NC)    - Clean up temporary files"

# Create virtual environment and install dependencies
venv:
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✅ Virtual environment created and dependencies installed$(NC)"
	@echo "$(YELLOW)To activate: source $(VENV_ACTIVATE)$(NC)"

# Install dependencies in existing venv
install:
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

# Run tests
test:
	@echo "$(BLUE)Running tests...$(NC)"
	$(PYTHON_VENV) -m pytest tests/ -v
	@echo "$(GREEN)✅ Tests completed$(NC)"

# Format code
format:
	@echo "$(BLUE)Formatting code...$(NC)"
	$(PYTHON_VENV) -m black agent/ tests/
	$(PYTHON_VENV) -m isort agent/ tests/
	@echo "$(GREEN)✅ Code formatted$(NC)"

# Lint code
lint:
	@echo "$(BLUE)Running linting checks...$(NC)"
	$(PYTHON_VENV) -m black --check agent/ tests/
	$(PYTHON_VENV) -m isort --check-only agent/ tests/
	$(PYTHON_VENV) -m mypy agent/
	@echo "$(GREEN)✅ Linting completed$(NC)"

# Run the rebalancing agent
run:
	@echo "$(BLUE)Starting rebalancing agent...$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop$(NC)"
	$(PYTHON_VENV) -m agent.runner

# Run the agent once (no scheduler)
run-once:
	@echo "$(BLUE)Running single rebalancing cycle...$(NC)"
	$(PYTHON_VENV) -m agent.runner --once

# Run in dry-run mode
run-dry:
	@echo "$(BLUE)Running in dry-run mode...$(NC)"
	$(PYTHON_VENV) -m agent.runner --dry-run

# Validate configuration
validate:
	@echo "$(BLUE)Validating configuration...$(NC)"
	$(PYTHON_VENV) -m agent.runner --validate

# Launch Jupyter Lab
notebook:
	@echo "$(BLUE)Launching Jupyter Lab...$(NC)"
	@echo "$(YELLOW)Navigate to notebooks/00_api_sanity.ipynb$(NC)"
	cd notebooks && $(PYTHON_VENV) -m jupyter lab

# Deploy to production
deploy:
	@echo "$(BLUE)Deploying to production...$(NC)"
	@if [ -z "$$(git status --porcelain)" ]; then \
		echo "$(GREEN)✅ Working directory clean$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Working directory has uncommitted changes$(NC)"; \
		git status --short; \
		echo "$(YELLOW)Committing changes...$(NC)"; \
		git add .; \
		git commit -m "Auto-commit before deploy"; \
	fi
	git push origin main
	@echo "$(GREEN)✅ Deployed to production$(NC)"

# Show project status
status:
	@echo "$(BLUE)Project Status$(NC)"
	@echo "$(GREEN)Python version:$(NC) $$($(PYTHON) --version)"
	@echo "$(GREEN)Virtual environment:$(NC) $(if $(wildcard $(VENV_ACTIVATE)),✅ Active,❌ Not found)"
	@echo "$(GREEN)Dependencies:$(NC) $(if $(wildcard requirements.txt),✅ Found,❌ Not found)"
	@echo "$(GREEN)Git status:$(NC)"
	@git status --short || echo "  Not a git repository"
	@echo "$(GREEN)Environment file:$(NC) $(if $(wildcard .env),✅ Found,⚠️  .env not found (using .env.example))"
	@echo "$(GREEN)Recent commits:$(NC)"
	@git log --oneline -5 || echo "  No git history"

# Clean up temporary files
clean:
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".ipynb_checkpoints" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

# Remove virtual environment
clean-venv:
	@echo "$(BLUE)Removing virtual environment...$(NC)"
	rm -rf $(VENV_DIR)
	@echo "$(GREEN)✅ Virtual environment removed$(NC)"

# Full clean (including venv)
clean-all: clean clean-venv
	@echo "$(GREEN)✅ Full cleanup completed$(NC)"

# Install development dependencies
install-dev:
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install pre-commit
	@echo "$(GREEN)✅ Development dependencies installed$(NC)"

# Setup pre-commit hooks
setup-hooks:
	@echo "$(BLUE)Setting up pre-commit hooks...$(NC)"
	$(PYTHON_VENV) -m pre_commit install
	@echo "$(GREEN)✅ Pre-commit hooks installed$(NC)"

# Run pre-commit on all files
check-all:
	@echo "$(BLUE)Running pre-commit on all files...$(NC)"
	$(PYTHON_VENV) -m pre_commit run --all-files
	@echo "$(GREEN)✅ Pre-commit checks completed$(NC)" 