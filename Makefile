# Makefile - WhatsApp Seller Bot (dev + prod helpers)
.PHONY: up dev down logs restart ps build push deploy clean clean-docker ingest shell health

# Config
COMPOSE := docker compose
PROJECT := whatsapp-seller-bot
REGISTRY ?= ghcr.io/yourusername
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")

# -------------------------
# Core lifecycle
# -------------------------
up:
	@echo ">>> Starting stack (build + detached)"
	$(COMPOSE) up -d --build

dev:
	@echo ">>> Starting dev stack (with override)"
	$(COMPOSE) -f docker-compose.yml -f docker-compose.override.yml up -d --build

down:
	@echo ">>> Stopping stack"
	$(COMPOSE) down

restart:
	@echo ">>> Restarting stack"
	$(COMPOSE) restart

ps:
	@echo ">>> Containers"
	$(COMPOSE) ps

logs:
	@echo ">>> Tailing logs (ctrl-c to exit)"
	$(COMPOSE) logs -f

# -------------------------
# Build & registry
# -------------------------
build:
	@echo ">>> Building images"
	$(COMPOSE) build --pull

push: build
	@echo ">>> Tag & push (uses REGISTRY=$(REGISTRY))"
	docker tag $(PROJECT)-backend:latest $(REGISTRY)/$(PROJECT)-backend:$(VERSION) || true
	docker tag $(PROJECT)-bot:latest $(REGISTRY)/$(PROJECT)-bot:$(VERSION) || true
	docker tag $(PROJECT)-dashboard:latest $(REGISTRY)/$(PROJECT)-dashboard:$(VERSION) || true
	docker push $(REGISTRY)/$(PROJECT)-backend:$(VERSION) || true
	docker push $(REGISTRY)/$(PROJECT)-bot:$(VERSION) || true
	docker push $(REGISTRY)/$(PROJECT)-dashboard:$(VERSION) || true

# -------------------------
# Utilities
# -------------------------
shell:
	@echo ">>> Shell into backend"
	$(COMPOSE) exec backend /bin/bash

ingest:
	@echo ">>> Ingesting products into vector DB"
	$(COMPOSE) exec backend python /app/backend/scripts/ingest_products.py

health:
	@echo ">>> Checking endpoints"
	@curl -fsS http://localhost:8000/health -m 3 && echo "  backend: OK" || echo "  backend: DOWN"
	@curl -fsS http://localhost:8501 -m 3 >/dev/null && echo "  dashboard: OK" || echo "  dashboard: DOWN"

# -------------------------
# Cleanup
# -------------------------
clean:
	@echo ">>> Removing Python caches and build artifacts"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

clean-docker:
	@echo ">>> Docker cleanup (containers, images, volumes)"
	$(COMPOSE) down -v --remove-orphans
	docker system prune -af --volumes

# -------------------------
# Convenience targets for CI
# -------------------------
ci-up: build
	@echo ">>> CI: starting stack for tests"
	$(COMPOSE) up -d

ci-down:
	@echo ">>> CI: tearing down"
	$(COMPOSE) down -v --remove-orphans
