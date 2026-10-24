@AGENTS.md

# Claude Code specifics

AGENTS.md above holds every project rule; this part only lists what Claude Code adds on top. Edit rules
in AGENTS.md, never here, so the two can never drift apart.

## Toolkit in .claude/
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
