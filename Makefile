.PHONY: help dev backend frontend test test-cov e2e lint lint-fix build \
        harness benchmark security-scan pull pull-all docker-up docker-down \
        logs health clean coverage docs verify

help:
	@echo ""
	@echo "  Asterion AI - Development Commands"
	@echo ""
	@echo "  === Dev ==="
	@echo "  make backend       Start FastAPI sidecar (port 8000)"
	@echo "  make frontend      Start Vite dev server (port 5173)"
	@echo ""
	@echo "  === Test ==="
	@echo "  make test          pytest (backend)"
	@echo "  make test-cov      pytest + coverage report"
	@echo "  make e2e           Playwright E2E tests"
	@echo "  make benchmark     Run model benchmark once (requires Ollama)"
	@echo ""
	@echo "  === Quality ==="
	@echo "  make lint          ruff + tsc --noEmit"
	@echo "  make lint-fix      ruff --fix"
	@echo "  make security-scan Secret scanner"
	@echo "  make build         Vite production build"
	@echo "  make harness       Meta-Harness smoke (phase 1, 3 iterations)"
	@echo ""
	@echo "  === Docker ==="
	@echo "  make docker-up     Start full stack (backend + searxng)"
	@echo "  make docker-down   Stop stack"
	@echo "  make logs          Stream backend logs"
	@echo ""
	@echo "  === Misc ==="
	@echo "  make pull          Pull required Ollama models"
	@echo "  make health        Check /api/health"
	@echo "  make clean         Remove build artifacts"
	@echo ""

backend:
	cd backend && uv run python -m asterion_api

frontend:
	cd frontend && npm run dev

test:
	cd backend && ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV=1 uv run pytest tests/ -v --tb=short

test-cov:
	cd backend && ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV=1 \
	  uv run pytest tests/ -v --tb=short \
	  --cov=asterion_api --cov-report=term-missing --cov-report=html

e2e:
	cd frontend && npx playwright test --reporter=list

benchmark:
	curl -s -X POST http://127.0.0.1:8000/api/benchmark/run \
	  -H "Content-Type: application/json" \
	  -d '{"runs_per_model":2,"max_tokens":64}' | python3 -m json.tool || python -m json.tool

lint:
	cd backend && uv run ruff check asterion_api tests
	cd frontend && npx tsc --noEmit

lint-fix:
	cd backend && uv run ruff check asterion_api tests --fix

security-scan:
	uv run python scripts/scan_secrets.py .

build:
	cd frontend && npm run build

harness:
	uv run python harness/meta_harness.py --phase 1 --iterations 3

docker-up:
	docker compose up --build

docker-down:
	docker compose down

logs:
	docker compose logs -f backend

health:
	@curl -s http://127.0.0.1:8000/api/health | python3 -m json.tool || python -m json.tool

pull:
	ollama pull llama3.2 && ollama pull nomic-embed-text

pull-all:
	ollama pull llama3.2 && ollama pull llama3.2:3b && ollama pull nomic-embed-text
	ollama pull codellama:7b && ollama pull phi3:mini && ollama pull qwen2.5:7b

clean:
	rm -rf frontend/dist frontend/.svelte-kit playwright-report test-results
	find backend -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; true
	rm -rf harness/candidates/candidate_*/

verify: lint test build security-scan harness
	@echo ""
	@echo "All checks passed. Ready to release."
