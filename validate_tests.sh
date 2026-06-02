#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
echo "==> [1/1] Django tests"
dropdb --if-exists test_barber_tenants_registry >/dev/null 2>&1 || true
python manage.py test --verbosity=1

echo "==> [1/1] All checks passed ✓"
