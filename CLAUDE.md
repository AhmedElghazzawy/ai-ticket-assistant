# CLAUDE.md: BŞEÜ Helpdesk Ticket Assistant

Instructions for Claude Code, the coding agent this project is built with (in the terminal). Keep this
file short: details live in the files linked below, which Claude reads when a task needs them.

## What this is
A course project (Çalışma Tasarımı I, BŞEÜ Computer Engineering) that is also a CV project. The system
reads a student's support ticket, labels it (category, priority, escalate), finds the answer in official
university documents (RAG), drafts a reply that cites its source, and decides in plain code: send it
automatically, or route it to the right office with the draft. Live demo: https://bseu-helpdesk.onrender.com

| Read this | When |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Before changing code: layers, request flow, data model, invariants |
| [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) | Labels, routing, data rules, the professor's requirements |
| [docs/ROADMAP.md](docs/ROADMAP.md) | What is done, what is next, current status and scores |
| [docs/decisions/](docs/decisions/) | Why a choice was made (ADRs, in Turkish) |
| [docs/labels.md](docs/labels.md) | The label rulebook (Turkish) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Setup, commands, commit and PR conventions |

## Who I am and how we communicate
- Computer engineering student, beginner in AI engineering. Mac, VS Code, Claude Code in the terminal.
- Chat with me in English, in simple words.
- Anything for my professor or the university (reports, emails, ADRs, the Turkish README) is in Turkish,
  with English technical terms kept as they are (RAG, API, embedding, classification...).
- I must be able to explain every line of this project to my professor myself.

## Teaching mode (always on)
- Auto mode stays OFF. Never run edits or commands without telling me first.
- For every step, in this order:
  1. Goal of the step in plain words, and why it matters for the project.
  2. A short plan: which files you will create or change.
  3. Wait for my OK.
  4. Build in SMALL pieces (never a whole big file at once), explaining each piece. Define every new term
     the first time it appears, with a short analogy if it helps.
  5. Run it and show me the real output.
  6. Ask me 2-3 short questions to check I understood, and wait for my answers. If I'm wrong, correct me
     kindly and re-explain.
  7. Suggest a commit message. Only commit when I say so. Every approved commit is pushed right away.
- After EVERY change (new file, code change, decision, problem found, command run and its result), add it
  to docs/changelog.md with the reason, then run `uv run python tools/make_context.py` so
  claude_context.md is up to date (the full project in one file, which I paste into a Claude chat to be taught).
- You may add the libraries and tools the project really needs. Before adding one, say what it is, why we
  need it, and the simpler alternative. Complexity that adds nothing is a weakness, not a strength.
- Tell me honestly when something is weak or may be misleading (for example an inflated score).
- If I say "I don't understand", explain it another way (analogy, tiny example) before moving on.

## Safety rules (never break these)
- Never read, print, copy or commit `.env`. It holds my API key. Placeholders only in `.env.example`. If
  `.env` is missing, ask me to create it; never ask me to paste a key into the chat.
- The locked test sets `data/tickets/test_tickets.jsonl` and `data/tickets/phase8_tickets.jsonl` are never
  edited and never used to tune a prompt. Only a final score is run on them, and only when I ask.
- Check current Gemini model names and limits in Google's official docs instead of assuming. The model
  name lives in `.env` as GEMINI_MODEL.
- The free tier has per-minute limits: short waits and automatic retries between calls, never a loop
  over many tickets without them.
- Never commit without asking me. When I approve a commit, push it right away. Larger work goes on a
  branch with a pull request, so CI checks it before it reaches main.
- Deploy commands (render, neonctl) are mine to run.

## Production standard
Judge every change by: "would a senior engineer approve this in code review?"
- Code: typed (mypy strict), ruff clean and formatted, small modules with one job, no dead code.
- Tests: every rule and every bug fix gets a test, written first. AI calls are faked in unit tests; real
  AI calls only in evals.
- CI: lint, types, tests, frontend checks and Docker build on every push. main is always green.
- Config: settings typed and validated at startup (pydantic-settings); no magic strings in code.
- Observability: structured logs; per ticket, latency, tokens, cost and the decision with its reasons.
  Never log student text or e-mail addresses.
- Evaluation: every metric reports its sample size and 95% confidence interval; results are versioned.
- Security: prompt-injection defence, no personal data in logs, staff pages behind a login, rate limits
  on public endpoints, secrets only in the environment.
- Docs: an ADR in docs/decisions/ for every major choice; README metrics always with sample sizes.
- Honesty: say when something is demo-grade, and what would make it production-grade.

## Commands
Run from the repository root. `make help` lists them all.

| Task | Command |
|---|---|
| Install everything | `make install` (`uv sync --locked` + `npm ci` in frontend/) |
| Start Postgres for tests | `make db` (docker compose up -d db) |
| Every check CI runs | `make check` |
| Python only | `make lint`, `make typecheck`, `make test` |
| Frontend only | `make web-check` |
| Run the whole app | `make up` (docker compose up --build), then http://127.0.0.1:8000 |
| API schema + client after an API change | `make api-client` |
| Refresh the teaching bundle | `uv run python tools/make_context.py` |

Evals call the paid model: run them only when asked, one suite at a time (see the `run-evals` skill).

## Code map
- `src/pipeline.py` one ticket end to end: classify, retrieve, draft, decide.
- `src/classifier.py`, `src/answer.py` the two LLM steps; `src/llm.py` the shared Gemini client.
- `src/fence.py`, `src/grounding.py` prompt-injection defence (ADR 0010).
- `src/knowledge_base.py`, `src/retrieval.py` chunks, embeddings, pgvector search.
- `src/decision.py` the auto-send rules: pure code, the most important file to keep tested.
- `src/store.py` Postgres, migrations; `src/auth.py` staff login; `src/api.py` FastAPI app.
- `src/evaluate*.py`, `src/stats.py` evals and Wilson intervals; results in `eval/`.
- `frontend/` React app (student chat, Taleplerim, staff console); its API client is generated.
- `tests/` pytest against a real Postgres; `tests/fakes.py` fakes every AI call.

## Agent loop (how every change is made)
1. **Explore.** Read the module, its tests and its ADR. Do not guess how something works.
2. **Plan.** Goal, files, risks, and how it will be verified. Teaching mode: wait for my OK.
3. **Test first.** A failing test that shows the rule or the bug.
4. **Implement** in small pieces that each keep the suite green.
5. **Verify.** `make check` passes; show the real output. A change that touches prompts or retrieval also
   needs an eval on the dev set, never on a locked set.
6. **Record.** docs/changelog.md entry with the reason, an ADR if a choice was made, docs/ROADMAP.md
   status if an item moved, then `tools/make_context.py`.
7. **Ship.** Suggest a commit message, commit after my OK, push the branch, open a PR.

Definition of done: checks green, tests for the new behaviour, changelog written, docs updated, and I
can explain the change.

## Conventions
- Python 3.12, snake_case, type hints everywhere, short English comments that say why, not what.
- Label IDs, code and comments in English (ASCII); user-facing text bilingual (TR and EN).
- Settings come from `config.py`; rules that change results (MIN_SCORE, prompts) stay in code on purpose,
  so changing them is a reviewed commit followed by a new eval.
- Database changes: append a new step to `MIGRATIONS` in `src/store.py`; never edit a released step.
- API changes: regenerate `frontend/openapi.json` and the client (`make api-client`); CI fails otherwise.
- Commits: one topic each, imperative summary line, the reason in the body.

## Claude Code toolkit (.claude/)
- **Skills** (`.claude/skills/`), loaded when a task matches:
  `quality-gate` (every CI check, in order), `teach-step` (the teaching-mode procedure),
  `run-evals` (safe, versioned eval runs), `new-adr` (decision records),
  `add-api-endpoint` (route + schema + test + generated client), `db-migration` (append-only migrations).
- **Subagents** (`.claude/agents/`), started only when I ask for one or a skill says so:
  `code-reviewer` (read-only review against the production standard), `test-writer` (the failing test
  first), `eval-analyst` (reads eval results, reports n and intervals, flags inflated scores),
  `security-auditor` (injection, PII, auth, secrets).
- **Guardrails** (`.claude/settings.json` + `.claude/hooks/`): reading or editing `.env` is denied; a
  hook blocks every edit to the locked test sets; safe check commands are allowed without a prompt.
  Personal permission tweaks go in `.claude/settings.local.json` (git-ignored).

## Session habits
- Start a task by reading the matching section of ARCHITECTURE.md and the ADRs it names.
- Use the `quality-gate` skill before saying anything is done.
- At the end of a session, propose an update of "Current status" in docs/ROADMAP.md and ask me first.
