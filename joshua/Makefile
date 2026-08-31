# ═══════════════════════════════════════════════════════════════
# Joshua — commandes de développement
# ═══════════════════════════════════════════════════════════════
.PHONY: install dev up down logs ingest import-rbi scan index test migrate lint clean help
.DEFAULT_GOAL := help

VENV    ?= .venv
PYTHON  ?= $(VENV)/bin/python
PIP     ?= $(VENV)/bin/pip

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Crée l'environnement virtuel et installe les dépendances
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@test -f .env || cp .env.example .env
	@echo "→ Renseignez .env (TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY) puis : make up"

dev: ## Lance Joshua en local (les services doivent tourner : make up)
	$(PYTHON) -m app.main

up: ## Démarre la pile Docker complète
	docker compose up -d --build
	@echo "→ Journaux : make logs"

down: ## Arrête la pile (les volumes sont conservés)
	docker compose down

logs: ## Suit les journaux de Joshua
	docker compose logs -f joshua

ingest: ## Ingère data/incoming/
	$(PYTHON) scripts/ingest.py data/incoming/

import-rbi: ## Importe le corpus documentaire du Rite Brith Israël
	$(PYTHON) scripts/import_rbi.py

scan: ## Inventorie la bibliothèque sans rien indexer
	$(PYTHON) scripts/index_library.py --scan

index: ## Indexe les nouveautés de la bibliothèque
	$(PYTHON) scripts/index_library.py --update

test: ## Lance la suite de tests
	$(PYTHON) -m pytest tests/ -v

migrate: ## Applique les migrations de schéma
	$(VENV)/bin/alembic upgrade head

clean: ## Supprime les fichiers temporaires Python
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	rm -rf .pytest_cache
