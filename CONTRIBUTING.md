# Contributing

How to set up, change and ship this project. Coding agents follow the same rules through
[AGENTS.md](AGENTS.md); the design is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Setup
Needs Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 24, and Docker.

```bash
make install            # uv sync --locked + npm ci
cp .env.example .env    # then put your own Gemini key in .env (never commit it)
make db                 # Postgres 18 + pgvector on 127.0.0.1:5433
make check              # every check CI runs
make up                 # the whole app at http://127.0.0.1:8000
```

Tests never call Gemini, so `make check` works without a key. Evals do call it; see
`.claude/skills/run-evals/SKILL.md` before running one.

## Making a change
1. Branch from `main`.
2. Write the failing test first: every rule and every bug fix gets one.
3. Keep modules small and typed; settings come from `src/config.py`.
4. API change: `make api-client` regenerates `frontend/openapi.json` and the TypeScript client.
5. Schema change: append a step to `MIGRATIONS` in `src/store.py`; never edit a released one.
6. A significant choice gets a decision record in `docs/decisions/` (Turkish, next number).
7. Add an entry to `docs/changelog.md`: what changed, why, the commands run and their results.
8. `make check` is green, then open a pull request. CI must pass before merge; `main` is always green.

## Commits and pull requests
- One topic per commit; the summary line says what changed, the body says why.
- A PR description says what changed, why, how it was verified, and what it does not do.
- Eval results are committed together with the change that produced them, with sample sizes and
  intervals. Never tune a prompt on `data/tickets/test_tickets.jsonl` or `phase8_tickets.jsonl`.

## Data and privacy
Student messages are personal data. Never log ticket text or e-mail addresses, never commit real
tickets, and keep secrets in the environment only.
