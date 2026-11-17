# CLAUDE.md

Guidance for Claude Code and other coding agents working in this repository. Human contributors
follow the same rules: [CONTRIBUTING.md](CONTRIBUTING.md).

## What this is
A helpdesk assistant for BŞEÜ students: it labels a ticket (category, priority, escalate), retrieves
the answer from official university documents (RAG), drafts a reply that cites its sources, and
decides in plain code whether to send it or route it to the right office with the draft.

| Read this | When |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Before changing code: layers, request flow, data model, invariants |
| [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) | Labels, routing, auto-send rule, data rules |
| [docs/decisions/](docs/decisions/) | Why a choice was made (ADRs, in Turkish) |
| [docs/labels.md](docs/labels.md) | The label rulebook (Turkish; also the classifier's prompt) |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Status, milestones, known gaps |

## Safety rules
- Never read, print, copy or commit `.env`; placeholders only in `.env.example`.
- The locked sets `data/tickets/test_tickets.jsonl` and `data/tickets/realistic_tickets.jsonl` are
  never edited and never used to tune a prompt; only final scores run on them (ADR 0003).
- Check Gemini model names and limits in Google's official docs instead of assuming.
- Evals make real model calls on the free tier: one suite at a time, with the built-in pauses, on the
  dev set unless a final score is asked for. Never loop over many tickets without waits.
- Never log ticket text or e-mail addresses.

## Engineering standard
- Typed (mypy strict), ruff clean and formatted, small modules with one job, no dead code.
- Every rule and every bug fix gets a test, written first. AI calls are faked in unit tests
  (`tests/fakes.py`); real calls only in evals.
- Settings are typed and validated at startup (`core/settings.py`, the only reader of the
  environment); rules that change results (thresholds, prompts) stay in code, so changing one is a
  reviewed commit followed by an eval.
- Every metric reports its sample size and 95% interval; results are versioned in `eval/`.
- Comments say why, not what. Label ids, code and comments in English; user-facing text TR and EN.

## Commands
Run from the repository root; `make help` lists them all.

| Task | Command |
|---|---|
| Install | `make install` |
| Postgres for tests | `make db` |
| Every CI check | `make check` |
| Python only | `make lint`, `make typecheck`, `make test` |
| Frontend only | `make web-check` |
| Whole app | `make up`, then http://127.0.0.1:8000 |
| API with reload | `make serve` (and `cd frontend && npm run dev`) |
| After an API change | `make api-client` |
| An eval | `make eval SUITE=classifier\|pipeline\|retrieval\|security [SET=...]` |

Use `make` or `uv run python -m helpdesk...`, never `python src/...` paths.

## Code map
Backend package `src/helpdesk/`. Layers import only layers below them (`tests/test_architecture.py`):
core <- domain <- ai, storage <- retrieval <- services <- api, evals.
- `core/` settings, paths, logs. `domain/` pure rules and data: `decision.py` (auto-send rules),
  `grounding.py`, `offices.py`, `tickets.py`, `outputs.py`, `records.py`.
- `ai/` the two model steps (`classifier.py`, `answer.py`), `fence.py` (injection fence), `gemini.py`,
  `resilience.py` (live model chain). `storage/` all SQL; `MIGRATIONS` in `db.py` are append-only.
- `retrieval/` chunks, embeddings, pgvector search. `services/` use cases; `errors.py` mapped to HTTP
  in `api/app.py`. `api/` thin routers, `app.py` is the composition root. `evals/` evals and intervals.
- `frontend/` React app with a generated API client. `tests/` pytest against a real Postgres.

## How a change is made
1. **Explore** the module, its tests and its ADR.
2. **Plan** goal, files, risks, verification.
3. **Test first**, then **implement** in small steps that keep the suite green.
4. **Verify** with `make check`; a prompt or retrieval change also needs a dev-set eval.
5. **Record** an entry in `docs/dev-notes/journal.md`, an ADR for a significant choice, ROADMAP and
   CHANGELOG.md if a milestone moved.
6. **Ship** on a topic branch with one PR; CI must be green before merge, and Render deploys main only
   after CI passes. Deploy commands (render, neonctl) are run by the maintainer.

Conventions: Python 3.12, one topic per commit, imperative summary line and the reason in the body;
API changes regenerate `frontend/openapi.json` and the client (CI fails otherwise).

## Toolkit (`.claude/`)
- Skills: `quality-gate`, `run-evals`, `new-adr`, `add-api-endpoint`, `db-migration`, `teach-step`.
- Subagents (only when asked): `code-reviewer`, `test-writer`, `eval-analyst`, `security-auditor`.
- Guardrails: `settings.json` denies reading `.env` and editing locked sets; `hooks/guard_files.py`
  blocks the same through any tool (tested in `tests/test_guard_files.py`).
- Personal instructions go in a git-ignored `CLAUDE.local.md`.
