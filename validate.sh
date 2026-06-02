#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==> [1/4] Linters (black, isort, flake8, djlint)"
black --check .
isort --check-only .
flake8 .
djlint barberia/**/templates --check

echo "==> [2/4] Security (bandit)"
bandit -r barberia/ -x barberia/tests --skip B105,B106,B311

echo "==> [3/4] Django tests"
dropdb --if-exists test_barber_tenants_registry >/dev/null 2>&1 || true
python manage.py test --verbosity=1

echo "==> [4/4] All checks passed ✓"
