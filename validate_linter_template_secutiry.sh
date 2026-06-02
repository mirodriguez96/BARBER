#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==> [1/3] Linters (black, isort, flake8, djlint)"
black --check .
isort --check-only .
flake8 .
djlint barberia/**/templates --check

echo "==> [2/3] Security (bandit)"
bandit -r barberia/ -x barberia/tests --skip B105,B106,B311

echo "==> [3/3] All checks passed ✓"
