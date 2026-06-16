.PHONY: help install dev test lint format type-check security clean examples check

PYTHON ?= python3
POETRY ?= poetry

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(POETRY) install --only main

dev: ## Install all dependencies (including dev)
	$(POETRY) install

test: ## Run tests
	$(POETRY) run pytest tests/ -v

lint: ## Run linters (ruff + black check)
	$(POETRY) run ruff check acmt001_lsp/ tests/
	$(POETRY) run black --check acmt001_lsp/ tests/

format: ## Auto-format code (ruff fix + black)
	$(POETRY) run ruff check --fix acmt001_lsp/ tests/
	$(POETRY) run black acmt001_lsp/ tests/

type-check: ## Run mypy type checking
	$(POETRY) run mypy acmt001_lsp/

security: ## Run security scan (bandit)
	$(POETRY) run bandit -r acmt001_lsp/ -ll

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .eggs/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/
	rm -rf coverage.xml .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

examples: ## Verify example scripts run
	$(POETRY) run python examples/lsp_helpers.py

check: lint type-check security test examples ## Run all checks
