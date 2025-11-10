# ──────────────────────────────
# MAT Engine Smart Rebuild Makefile
# ──────────────────────────────

# Detect changes using git diff and rebuild only affected services
smart-rebuild:
	@echo "Detecting changes since last commit..."
	$(eval CHANGED := $(shell git diff --name-only HEAD~1 HEAD 2>/dev/null || git ls-files --modified))
	@echo "Changed files:\n$(CHANGED)\n"

	$(eval REBUILD_API := $(shell echo "$(CHANGED)" | grep -q '^api/' && echo true || echo false))
	$(eval REBUILD_ML := $(shell echo "$(CHANGED)" | grep -q '^ml-worker/' && echo true || echo false))
	$(eval REBUILD_UI := $(shell echo "$(CHANGED)" | grep -q '^ui/' && echo true || echo false))

	@if [ "$(REBUILD_API)" = "true" ]; then \
		echo "Rebuilding API service..."; \
		docker compose build --no-cache api; \
	fi

	@if [ "$(REBUILD_ML)" = "true" ]; then \
		echo "Rebuilding ML Worker service..."; \
		docker compose build --no-cache ml-worker; \
	fi

	@if [ "$(REBUILD_UI)" = "true" ]; then \
		echo "Rebuilding UI service..."; \
		docker compose build --no-cache ui; \
	fi

	@if [ "$(REBUILD_API)$(REBUILD_ML)$(REBUILD_UI)" = "falsefalsefalse" ]; then \
		echo "No service-level changes detected. Nothing to rebuild."; \
	else \
		echo "\n Restarting stack..."; \
		docker compose up -d; \
	fi


rebuild-api:
	docker compose build --no-cache api && docker compose up -d && docker logs -f matengine-api

rebuild-ml:
	docker compose build --no-cache ml-worker && docker compose up -d && docker logs -f matengine-ml

rebuild-ui:
	docker compose build --no-cache ui && docker compose up -d && docker logs -f matengine-ui

rebuild-all:
	docker compose build --no-cache && docker compose up -d

logs-api:
	docker logs -f matengine-api

status:
	docker compose ps
