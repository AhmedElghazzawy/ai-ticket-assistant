# Roadmap

What is built, what is next, and the known gaps. Every change and its measured result is in the
engineering journal ([dev-notes/journal.md](dev-notes/journal.md)); releases in
[CHANGELOG.md](../CHANGELOG.md).

## Current status (2026-11-17)
Live at https://bseu-helpdesk.onrender.com (Render free + Neon, Frankfurt). 314 backend tests
(coverage 88%) and 30 Playwright runs, CI green, 18 ADRs. Latest measured scores (details and intervals
in the README):
- Locked test set (n=40): all three labels right 73.8% (mean of 2 runs; per-run 95% CI about 57–86%),
  0 of 14 missed escalations.
- Locked realistic set (n=40): all three labels right 72.5% (57–84%), 0 of 11 missed escalations;
  pipeline 0 unsafe auto-sends, 15/40 answered automatically.
- Retrieval: hit@3 100% on dev (n=47, 92–100%) and realistic (n=30, 89–100%); hit@1 91% on dev.
- Prompt injection: 12/12 attack probes safe.

## Milestones

| Milestone | Status | What it delivered |
|---|---|---|
| Ticket classifier | Done | 7 categories, 4 priorities, escalation rules ([labels.md](labels.md)); structured output; dev set and a locked test set (ADR 0003); Wilson 95% intervals |
| Grounded answers | Done | 28 official documents (190 chunks, TR + EN); pgvector search; replies that cite their sections; evidence checked word for word in code; auto-send decided in plain code (ADR 0002, 0010, 0013) |
| Platform | Done | FastAPI app factory, typed settings, structured logs without student text, Docker, CI (lint, types, tests, frontend, build), CodeQL, Dependabot; layered package with an enforced import rule (ADR 0012) |
| Staff console | Done | Login, per-office queue, edit and send, reassign, demo mode (ADR 0006), first help on forwarded tickets (ADR 0008), Insights page, append-only ticket history (ADR 0017) |
| Student follow-up | Done | "Taleplerim" with a secret code (ADR 0009), feedback, the decision trace, "Send to a specialist" (ADR 0016) |
| Security | Done | Prompt-injection fence and 12 probes (ADR 0010), rate limits and a daily cap, CSRF, trusted client-IP header (ADR 0007), Argon2id logins with lockout |
| Live deployment | Done | Render + Neon (ADR 0005), deploy only after CI; hedged chain of free Gemini models with a 25 s limit (ADR 0018) |
| Evaluation platform | Partial | Done: one command (`make eval`), versioned results (commit, prompt, dataset and KB hashes). Next: eval workflow in CI, model comparison |
| Hybrid retrieval | Next | Postgres full-text search + pgvector with reciprocal rank fusion; hit@1 and MRR before/after |
| Larger evaluation set | Next | 200+ labelled dev tickets (LLM-drafted candidates, every label reviewed by the maintainer); model comparison incl. a local open model |
| Tracing | Next | OpenTelemetry spans per ticket (classify, embed, search, answer, which model answered), local Jaeger |
| Better advice | Next | "What you can do" steps that end with who to contact; needs a dev eval |
| Follow-up questions | Later | Ask the student for missing details; only if the loop earns its complexity |

## Known gaps
- **Free hosting sleeps** after 15 minutes; the first visitor waits ~30 s. GitHub's scheduled
  keep-awake job runs only every 4–7 hours; a free external monitor on `/api/health` fixes it.
- **One labeller:** every label is the maintainer's; no second-rater agreement score yet.
- **Synthetic data:** tickets are written from real BŞEÜ systems and common problems, not collected
  from real students.
- **Brand:** the official BŞEÜ logo is not used without the university's permission.
- **Release:** no v1.0 tag or demo video yet.
