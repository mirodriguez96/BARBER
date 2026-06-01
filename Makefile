.PHONY: help lint lint-fix security test build deploy clean

.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

lint: ## Run all linters (check only)
	black --check .
	isort --check-only .
	flake8 .
	djlint barberia/**/templates --check

lint-fix: ## Auto-fix lint issues (black, isort)
	black .
	isort .

security: ## Run security scanners
	bandit -r barberia/ -x barberia/tests
	safety check -r requirements.txt

test: ## Run Django test suite
	python manage.py test --verbosity=2

build: ## Build Docker image
	docker compose build

deploy: ## Trigger deploy via GitHub Actions
	@echo "Push to main branch to trigger CI/CD pipeline."
	@echo "Or use: git push origin main"

clean: ## Clean Python cache artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
