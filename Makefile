ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
BACKEND_DIR := $(ROOT_DIR)backend
PYTHON := $(if $(wildcard $(ROOT_DIR).venv/bin/python),$(ROOT_DIR).venv/bin/python,python3)
COMPOSE := docker compose

.PHONY: db-up backend-build migrate migrate-current migrate-history migrate-local migrate-current-local migrate-history-local

db-up:
	cd $(ROOT_DIR) && $(COMPOSE) up -d db

backend-build:
	cd $(ROOT_DIR) && $(COMPOSE) build backend

migrate: db-up backend-build
	cd $(ROOT_DIR) && $(COMPOSE) run --rm backend python -m alembic upgrade head

migrate-current: db-up backend-build
	cd $(ROOT_DIR) && $(COMPOSE) run --rm backend python -m alembic current

migrate-history: backend-build
	cd $(ROOT_DIR) && $(COMPOSE) run --rm backend python -m alembic history

migrate-local:
	cd $(BACKEND_DIR) && $(PYTHON) -m alembic upgrade head

migrate-current-local:
	cd $(BACKEND_DIR) && $(PYTHON) -m alembic current

migrate-history-local:
	cd $(BACKEND_DIR) && $(PYTHON) -m alembic history