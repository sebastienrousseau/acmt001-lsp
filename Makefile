# SPDX-License-Identifier: Apache-2.0 OR MIT
# Convenience targets for acmt001-lsp.
#
# Every gate runs what CI runs, from the same hash-pinned requirements.
# `make install` builds that environment in .venv.

PY ?= .venv/bin/python
PKG := acmt001_lsp

.PHONY: help install test lint format type-check security complexity verify-versions audit pip-compile fuzz examples bench check clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Create/refresh .venv from the hash-pinned CI tree
	python3 -m venv .venv
	$(PY) -m pip install --require-hashes -r requirements/ci.txt
	$(PY) -m pip install --no-deps --no-build-isolation -e .

test: ## Run tests with the 100% coverage gate
	$(PY) -m pytest tests/ -v

# Same paths CI lints, so a green `make lint` means a green lint job.
LINT_PATHS := $(PKG) tests benches scripts examples fuzz

lint: ## Ruff lint and black format check (what CI runs)
	$(PY) -m ruff check $(LINT_PATHS)
	$(PY) -m black --check $(LINT_PATHS)

format: ## Auto-format code (ruff fix + black)
	$(PY) -m ruff check --fix $(LINT_PATHS)
	$(PY) -m black $(LINT_PATHS)

type-check: ## Run mypy type checking
	$(PY) -m mypy $(PKG)/

security: ## Run security scan (bandit)
	$(PY) -m bandit -r $(PKG)/ -ll

complexity: ## Per-function complexity ceilings against complexity-baseline.json
	$(PY) scripts/check_complexity.py

verify-versions: ## Every restatement of the version agrees with pyproject.toml
	$(PY) scripts/verify_versions.py

audit: ## pip-audit every hash-pinned requirements file (needs pip-audit)
	@for f in requirements/*.txt; do \
		echo "--- $$f"; \
		pip-audit --progress-spinner off --require-hashes --disable-pip -r "$$f" || exit 1; \
	done

pip-compile: ## Regenerate hash-pinned requirements/*.txt from requirements/*.in (needs uv)
	@command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/"; exit 1; }
	@for f in requirements/*.in; do \
		case "$$f" in requirements/fuzz.in|requirements/audit.in) continue;; esac; \
		echo "compiling $$f"; \
		uv pip compile --quiet --generate-hashes --universal \
			--python-version 3.11 "$$f" -o "$${f%.in}.txt"; \
	done
	@echo "compiling requirements/audit.in (3.12, the Security workflow's pip-audit Python)"
	@uv pip compile --quiet --generate-hashes --universal \
		--python-version 3.12 requirements/audit.in -o requirements/audit.txt
	@echo "compiling requirements/fuzz.in (Linux x86_64, Atheris wheels only)"
	@uv pip compile --quiet --generate-hashes --python-platform x86_64-manylinux_2_17 \
		--python-version 3.12 requirements/fuzz.in -o requirements/fuzz.txt

fuzz: ## Atheris for FUZZ_SECONDS (default 60); Linux x86_64, needs requirements/fuzz.txt
	$(PY) fuzz/fuzz_documents.py fuzz/corpus -max_total_time=$(or $(FUZZ_SECONDS),60)

examples: ## Run every example end-to-end
	@for e in examples/*.py; do echo "--- $$e ---"; $(PY) "$$e" || exit 1; done

bench: ## The benchmark in quick mode (what CI runs)
	$(PY) benches/bench_diagnostics.py --quick

check: lint type-check security complexity verify-versions test examples bench ## Run every gate CI runs on a pull request

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .eggs/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/
	rm -rf coverage.xml .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
