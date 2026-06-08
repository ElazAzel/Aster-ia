# Contributing

Asterion AI is a local-first desktop AI workspace. Contributions should preserve privacy-by-default behavior and the BaseHarness service contract.

## Local Setup

```powershell
cd backend
uv sync --extra dev
uv run python -m asterion_api
```

```powershell
cd frontend
npm ci
npm run dev
```

Optional Docker dev loop:

```powershell
docker compose up --build
```

## Verification

Run the same checks before pushing:

```powershell
uv run python -m compileall backend\asterion_api harness\meta_harness.py
cd backend
uv run ruff check .
uv run pytest
cd ..\frontend
npm run build
cd ..
uv run python harness/meta_harness.py --phase 1 --iterations 3
```

If touching Tauri, run `cargo check` in `src-tauri` after Visual C++ Build Tools are installed on Windows.

## Code Rules

- Keep backend IO async at service boundaries.
- Implement `BaseHarness.execute()`, `get_state()`, and `set_state()` for services that Meta-Harness can optimize.
- Add `privacy_level` to services: `local`, `hybrid`, or `external`.
- Run privacy checks before memory writes, web access, plugin execution, model API routing, and file indexing.
- Update `docs/updates.md` for user-visible, API, architecture, or release changes.
