---
name: quality-gate
description: Run every check CI runs (ruff, mypy strict, pytest on Postgres, OpenAPI drift, Biome, TypeScript, build) before saying a change is done or before a commit.
---

# Quality gate

Use this before you say a change is done, before you suggest a commit, and after a rebase. CI on GitHub
runs the same checks; a red check here is a red check there.

## Steps
1. Make sure Postgres answers on 127.0.0.1:5433 (`pg_isready -h 127.0.0.1 -p 5433`). If it does not:
   `make db` on a laptop; in a cloud session the SessionStart hook starts it.
2. Run `make check`. It runs, in CI order:
   - `uv run ruff check` and `uv run ruff format --check`
   - `uv run mypy` (strict: src, tests, tools and the agent hooks)
   - `uv run pytest` with coverage
   - `tools/export_openapi.py` + `git diff --exit-code frontend/openapi.json`
   - frontend: `npx biome ci .`, `npm run typecheck`, `npm run build`
3. Show the real output to the user: the last lines of each step, the test count and coverage.
4. If a step fails, fix the cause, never the check. Do not add `# type: ignore`, `noqa`, skip a test, or
   lower a coverage threshold to get green. If a fix needs that, stop and explain why to the user.
5. Browser tests (`npm run test:e2e` in frontend/) run in CI; run them locally when the UI changed.

## Formatting fixes
`uv run ruff format` and `uv run ruff check --fix` may be run to fix style. Tell the user what changed.

## Done means
All steps green, the new behaviour has a test, docs/changelog.md has an entry with the reason.
