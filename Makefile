.PHONY: dev docker-up docker-down backend frontend verify backend-verify frontend-build harness clean

dev:
	@echo "Run backend and frontend in separate terminals:"
	@echo "  make backend"
	@echo "  make frontend"

backend:
	cd backend && uv run python -m asterion_api

frontend:
	cd frontend && npm run dev

docker-up:
	docker compose up --build

docker-down:
	docker compose down

verify: backend-verify frontend-build harness

backend-verify:
	cd backend && uv run ruff check . && uv run pytest
	uv run python -m compileall backend/asterion_api harness/meta_harness.py

frontend-build:
	cd frontend && npm run build

harness:
	uv run python harness/meta_harness.py --phase 1 --iterations 3

clean:
	cd frontend && npm run build -- --emptyOutDir
