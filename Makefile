PYTHON_PATHS := plugin/runner tools tests

.PHONY: setup check test fmt contract

setup:
	uv sync --locked

fmt:
	uv run ruff format $(PYTHON_PATHS)
	uv run ruff check --fix $(PYTHON_PATHS)

# Four workers, not -n auto: several lanes run the tests at once on one computer (SPEC §7.3).
test:
	uv run pytest -n 4

# On demand, by the owner: the real claude and gh, on this repository (tests/contract).
contract:
	uv run pytest -m contract -v

check:
	uv run ruff format --check $(PYTHON_PATHS)
	uv run ruff check $(PYTHON_PATHS)
	uv run mypy
	PYTHONPATH=plugin/runner uv run lint-imports
	uv run complexipy $(PYTHON_PATHS) --max-complexity-allowed 15 --failed --quiet
	uv run python tools/check_limits.py $(PYTHON_PATHS)
	uv run python tools/validate_plugin.py plugin .
	uv run pytest -n 4 --cov --cov-report=term
	uv run pip-audit --strict --progress-spinner off
