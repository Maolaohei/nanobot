#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip >/dev/null
pip install pre-commit >/dev/null
pre-commit install >/dev/null

echo "pre-commit installed. Run 'pre-commit run --all-files' to fix issues."