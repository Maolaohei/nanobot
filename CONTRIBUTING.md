# Developer Experience

This project uses pre-commit and CI to keep code quality consistent.

Quick start:

- pip install -U pip pre-commit
- pre-commit install
- pre-commit run --all-files  # auto-fix ruff/black/isort

CI runs on Python 3.11/3.12/3.13 with ruff, black, isort, mypy and pytest.
