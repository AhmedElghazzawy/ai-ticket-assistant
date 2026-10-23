# Çalışma Tasarımı I: University Helpdesk Ticket Assistant

## What this is
A course project at BŞEÜ (Computer Engineering). The system reads a student's support ticket, labels it (category, priority, escalate), finds the answer in official university documents (RAG), drafts a reply that cites its source, and decides: send it automatically, or hand it to a human together with the draft and the right office.
It is also my FIRST AI engineering project. The goal is for me to learn and truly understand it, not just to have working code.

## Who I am and how we communicate
- Computer engineering student, complete beginner in AI engineering. Mac, VS Code, Claude Code in the terminal.
- Chat with me in English, in simple words.
- Anything written for my professor or the university (reports, emails, README for the course) is in Turkish, with English technical terms kept as they are (RAG, API, embedding, classification...).
- I must be able to explain every line of this project to my professor myself.

## Teaching mode (always on)
- Auto mode stays OFF. Never run edits or commands without telling me first.
- For every step, in this order:
  1. Goal of the step in plain words, and why it matters for the project.
  2. A short plan: which files you will create or change.
  3. Wait for my OK.
  4. Build in SMALL pieces (never a whole big file at once), explaining each piece. Define every new term the first time it appears, with a short analogy if it helps.
  5. Run it and show me the real output.
  6. Ask me 2-3 short questions to check I understood, and wait for my answers. If I'm wrong, correct me kindly and re-explain.
  7. Suggest a commit message. Only commit when I say so. Every approved commit is pushed to GitHub right away, so GitHub is always up to date.
- After EVERY change (new file, code change, decision, problem found, command run and its result), add it to docs/changelog.md with the reason, then run `uv run python tools/make_context.py` so claude_context.md is up to date. claude_context.md is the full project in one file, which I paste into a Claude chat to be taught.
- You may add the libraries, tools and setup the project really needs to reach production level. Before adding one, say what it is, why we need it, and what the simpler alternative would be. Every tool must earn its place: complexity that adds nothing is a weakness, not a strength.
- Keep code short and readable: small functions, type hints, short English comments, snake_case names.
- Tell me honestly when something is weak or may be misleading (for example an inflated score), even if I did not ask.
- If I say "I don't understand", explain it another way (analogy, tiny example) before moving on.

## Safety rules
- Never read, print, copy or commit .env. It holds my API key. The file must be named exactly .env and be listed in .gitignore.
- Keep a .env.example that contains only placeholders (GEMINI_API_KEY=your-key-here, GEMINI_MODEL=...). If .env does not exist, ask me to create it, and never ask me to paste the key into the chat.
- Check the current Gemini model names and free-tier limits in Google's official docs instead of assuming. The model name lives in .env as GEMINI_MODEL, so it can change without editing code.
- The free tier has request limits per minute. Add short waits between calls and automatic retries, and never loop over many tickets without that.
- Never commit without asking me first. When I approve a commit, push it to GitHub too (git push origin main).
- AGENTS.md is a copy of this file for Codex. Whenever this file changes, update AGENTS.md the same way.

## Production standard (decided 2026-10-11)
This is a CV project and must look like work from a strong industry team, not a course demo. Judge every step by: "would a senior engineer approve this in code review?"
- Code: typed (mypy passes), linted and formatted (ruff), small modules with one job each, no dead code.
- Tests: every rule and every bug fix gets a test. AI calls are faked in unit tests; real AI calls only in evals.
- CI: GitHub Actions runs lint, type checks and tests on every push. main must always be green.
- Config: settings typed and validated at startup (pydantic-settings); no magic strings scattered in code.
- Observability: structured logs; for every ticket record latency, tokens, cost and the decision with its reasons.
- Evaluation: every metric reports its sample size and confidence interval; evals can run on demand and their results are versioned; the locked test set stays locked.
- Security: prompt-injection defence, no personal data in logs, staff pages behind a login, rate limiting on public endpoints, secrets only in .env.
- Packaging: Docker, so anyone can run the full system with one command.
- Docs: README with an architecture diagram, real metrics and a demo link; short decision records (docs/decisions/) for every major choice.
- Honesty: say when something is demo-grade, and what would make it production-grade.

## What my professor asked for (his feedback on my idea)
He said the idea is feasible but too general. Before building, I must define clearly:
- which kinds of tickets, which units handle them, and what the results are
- how many ticket categories, and which ones
- which data and which documents the retrieval (RAG) part uses
- how the system will be evaluated
- the scope and limits
He also said these parts can be explained separately: classification, RAG retrieval, answer generation, and the forward / do-not-forward decision. His suggested flow: user submits ticket, system classifies it, RAG retrieves information from the knowledge base, a draft answer is created, the system decides on automatic reply, and unresolved or special cases go to the relevant unit or person.

## Project design (decided)
Categories (7): account_access, registration, billing, it_support, academic_records, campus_life, other
(campus_life replaced housing: the dorms in Bilecik are KYK dorms run by the state, not by BŞEÜ.)
Priority: low, medium, high, urgent
Escalate to a human when ANY applies: safety threat, harassment, or signs of crisis; account possibly compromised; the student needs a policy exception; a money or official-record error needing a refund or correction (the student says the system or their record is wrong); a grade or exam dispute, or a decision about whether an exam counts (e.g. the system crashed during the exam); a legal threat, a disciplinary case, or repeated contact with no answer. Being upset alone is NOT a reason.
Routing to units (real BŞEÜ offices): account_access and it_support go to Bilgi İşlem Daire Başkanlığı (IT); registration and academic_records go to Öğrenci İşleri Daire Başkanlığı (Student Affairs); billing goes to Öğrenci İşleri, İstatistik Disiplin ve Harçlar Şube Müdürlüğü (fees); campus_life goes to Sağlık, Kültür ve Spor (SKS) Daire Başkanlığı; other goes to Student Affairs duty staff.
BŞEÜ system names used in tickets and documents: OBS (student system), SOFRA (passwords and student e-mail), @ogrenci.bilecik.edu.tr e-mail, UZEM at ders.bilecik.edu.tr (distance courses), Akıllı Kart (student ID card). See docs/problem_catalog.md.

Pipeline (target): ticket -> classify -> retrieve document chunks -> draft reply that cites its source -> decide -> auto-send or route to a unit.
Auto-send only if ALL pass: category is not "other"; the model did not ask to escalate; priority is not "urgent" (a person can act today); retrieval found a strong match; the documents really answer the ticket; the draft cites a retrieved source. Otherwise route to the office (src/decision.py, tested in tests/test_decision.py).

## Data rules
- Language: the system is bilingual, Turkish and English. The user picks the language in the app, and everything they see (UI text, draft replies) is in that language. Tickets come in both languages, and every knowledge-base document exists in both Turkish and English. docs/labels.md (the label rulebook) is in Turkish. Label IDs (account_access, ...), code and comments stay in English, because code needs simple ASCII names.
- I write and label the tickets myself. You may suggest tickets that cover gaps (edge cases, tricky wording), but the final labels are my decision. Discuss each label with me and explain why.
- Format: data/tickets/tickets.jsonl (dev) and data/tickets/test_tickets.jsonl (locked test set), one JSON object per line: id, text, language (tr or en), category, priority, escalate. data/tickets/expected_docs.jsonl: for every ticket, the knowledge-base document that answers it, or none.
- Phase 1 has about 80 tickets (40 Turkish + 40 English) and no more. Phase 2 adds about 40 more (20 + 20), and those 40 are a LOCKED TEST SET: never used to adjust the prompt, only for the final score. Never tune the prompt on the test set.

## Tech stack (introduced one at a time, when needed)
Python 3.12 with a virtual environment in .venv (use uv if it is installed, otherwise ask me). In use: google-genai (gemini-3.5-flash-lite + gemini-embedding-2), pydantic + pydantic-settings, FastAPI + uvicorn (API, also serves the built web app), Postgres 18 + pgvector (ticket store and knowledge-base search; locally in Docker, production Neon), psycopg 3 with a connection pool, pytest + httpx2 (tests), uv (pyproject.toml + uv.lock), ruff (lint + format), mypy (strict), GitHub Actions (CI). Web app (frontend/): React 19 + TypeScript + Vite, Tailwind CSS + shadcn/ui (Base UI), TanStack Router + Query, types generated from the OpenAPI schema (@hey-api/openapi-ts), Biome, Playwright. Streamlit (old panel: overview, dataset, evaluation; to be replaced by the Insights page). Hosting: Render (free web service, Frankfurt) + Neon (production Postgres, Frankfurt). Planned (roadmap): hybrid search (keyword + embedding). Possible: LangGraph.

## Repo layout (target)
data/tickets/, data/knowledge_base/, src/, frontend/ (React web app: student chat + staff console), tests/ (pytest), tools/, eval/, docs/, README.md, CLAUDE.md, pyproject.toml, uv.lock, .env.example, .gitignore

## Phase 1: rebuild from zero, understanding every step
Everything was deleted on purpose so I can rebuild it slowly. Do NOT recreate the old code from memory or paste big files. Build it with me, step by step, using the teaching mode above.
- Step 0: Environment. Check Python 3.12, the virtual environment, .gitignore, .env.example, pyproject.toml. Help me create .env without ever reading it. Explain what each file is for.
- Step 1: First model call. Create src/llm.py (shared Gemini setup: key from .env, model name from GEMINI_MODEL, automatic retries) and a tiny test script that sends one ticket and prints the reply. Explain what an API call is.
- Step 2: Define the labels together. Before any code, we write the category definitions, priority definitions and escalation rules in plain words. I write them, you check them for overlaps and gaps.
- Step 3: The data. src/tickets.py defines what a valid ticket is (pydantic model, Literal types for category and priority) and loads tickets.jsonl with clear errors. I write the first 20 tickets with you; we reach about 80 (half Turkish, half English) with a good mix in each language: every category, every priority, edge cases, and about a quarter that need escalation.
- Step 4: The classifier. src/classifier.py: the system prompt built from our definitions, structured output (response schema), temperature left at the default 1.0 (Google's official Gemini 3 advice: below 1.0 can cause looping or degraded performance; consistency comes from structured output and clear rules, and is measured in Step 5 by running twice), thinking level "low" (compare with "high" in Step 5), and the "reason" field first. Explain why each choice matters. Run it on the tickets and read every mistake together.
- Step 5: The evaluation. src/evaluate.py: score per label and overall, and missed escalations (the most dangerous error: a ticket that needed a human but was not escalated). Save the run to eval/results_<thinking level>.json (results_low.json, results_high.json; the locked test set: results_high_test.json). Explain what the score does and does not prove.
- Step 6: A small web page. src/app.py with Streamlit: try one ticket, browse the dataset, run the evaluation. Keep it small and explain it block by block.
- Step 7: Review and package. I explain the whole flow back in my own words, we write a short README, and prepare what I show my professor (in Turkish): the categories and units table, the dataset description, the evaluation method and the first score.

Phase 1 is done when:
- I can explain every file in my own words.
- I wrote the labels and agree with them.
- I understand what the first score means and what it does NOT prove (the prompt was adjusted while looking at the same tickets, so the number is optimistic until Phase 2's locked test set).
- Everything is committed and pushed.

## Later phases (one deliverable per week for my professor)
2. Week 3: trustworthy score. About 120 tickets total, 40 locked as the test set, compare dev score and test score for each language, read every mistake.
3. Weeks 4-5: knowledge base of 8-10 short policy documents, each in Turkish and English, chunking, embeddings, retrieval. In-memory search first, then pgvector. Measure how often the right document is in the top 3.
4. Week 6: grounded draft replies that cite their source, the decision function, routing to units. Rate 15 drafts; count tickets auto-sent that should not have been.
5. Week 7: FastAPI endpoint POST /tickets, saved results, pytest tests for the decision rules.
6. Week 8: rebuild as a LangGraph graph, add a human review queue tab in Streamlit. (Status 2026-10-17: the review queue was built, first in Streamlit, now in the React staff console; the LangGraph rebuild was NOT done. The pipeline is a plain Python function (src/pipeline.py), which is enough for a straight line of steps; LangGraph stays "possible" if the flow ever needs loops or branches.)

## Roadmap to production (from 2026-10-11)
Phases 1-6 are done. Professor deliverables continue weekly alongside this.
Status key: [DONE], [PARTIAL] (what is done / what is left), [IN PROGRESS], [TODO]. Updated 2026-10-17.
7.  [DONE] Foundation: ruff + mypy, pydantic-settings config, structured logging, GitHub Actions CI, Docker (docker compose).
8.  [IN PROGRESS] Data: richer and more realistic tickets (multi-issue, typos, mixed TR/EN), a second person labels a sample (agreement score, Cohen's kappa), real tickets from classmates as a new unseen test set. Done: tools/audit_data.py and its findings (changelog, "Phase 8"). No second labeler or classmates' tickets are available: plan is realistic synthetic tickets, my own re-labeling a few days later (intra-rater agreement) and Claude-vs-me agreement, reported as exactly that. Left: write the new tickets (I decide every label), re-label sample, agreement scores.
9.  [PARTIAL] Evaluation: confidence intervals, LLM-as-judge for reply quality checked against my own ratings, one command that runs every eval and saves a versioned report; model comparison: the same locked evaluation on 3-4 LLMs (bigger Gemini, Claude, GPT, an open-weight model for KVKK / on-premise), choosing by accuracy, missed escalations, cost per 1,000 tickets and latency. Done: Wilson 95% intervals in the classifier eval (src/stats.py, src/evaluate.py, 2026-10-23). Left: intervals in the retrieval and pipeline evals, LLM-as-judge, one-command versioned report, model comparison.
10. [PARTIAL] Retrieval: Postgres + pgvector, hybrid search (keyword + embedding), reranking; measure each against the current hit@3. Done: Postgres + pgvector for tickets and knowledge-base search (same hit@3). Left: hybrid search, reranking (hit@3 is already 100%, so harder tickets from Phase 8 are needed first to see any gain).
11. [PARTIAL] Security and stress tests: prompt injection, empty or huge input, two problems in one ticket, PII handling, rate limiting; ONE final run on the locked test set. Done: rate limits (per visitor + daily cap), login limit, CSRF, fake-IP protection verified live, no student text in logs, input length limits. Left: a prompt-injection and stress test suite, PII handling, the one final locked-test run.
12. [PARTIAL] Staff product: a real staff dashboard (login, queue, edit and send), the reply actually reaches the student, ticket status the student can see. Done: login, per-office queue, edit and send, reassign, demo mode. Left: the reply reaching the student (e-mail), student-visible ticket status, Insights page (replaces Streamlit).
13. [PARTIAL] Deployment: live demo URL, monitoring of cost and errors. Done: live at https://bseu-helpdesk.onrender.com (Render free, Frankfurt + Neon Postgres, Frankfurt), verified live. Left: monitoring of cost and errors; Render setting "deploy only after CI checks pass" (dashboard); the free plan sleeps after 15 min.
14. [PARTIAL] Showcase: README with diagram and metrics, decision records, Turkish report for my professor, 5-minute demo, v1.0 tag. Done: Turkish README (demo link, screenshots, diagram, metrics with sample sizes and intervals), docs/decisions/ (7 records), release v0.9. Left: Turkish report, 5-minute demo, browser tests (Playwright installed, no tests yet), v1.0 tag.

## Lessons from my first attempt
- Claude Code ran in auto mode and wrote more than I understood. That is why we restarted.
- The first score of 85% came from a prompt tuned on the same tickets, so it was probably optimistic.
- The secrets file was once named key.env by mistake, so git did not ignore it. The name must be exactly .env.

## Current status
(2026-10-17) Phases 1-7 done (Phase 6 without the LangGraph rebuild); Phases 10-14 partly done; Phase 8 in progress (see the roadmap above for done / left per phase). Live demo: https://bseu-helpdesk.onrender.com (student chat TR/EN; staff console via "Demo olarak dene"). Release v0.9 on GitHub. Locked test: 73.8% all three labels (mean of 2 runs: 72.5% and 75.0%, per-run 95% CI about 57-86%, n=40), 0 missed escalations of 14, hit@3 17/17, 1 low-harm wrong auto-send (gap since closed). 90 tests, CI green (lint, mypy strict, tests on real Postgres, frontend, Docker build). Open items for the next session, in order: (1) I email my professor (draft: docs/professor_email.md, Turkish, not sent yet; README "Hocam, nereden başlamalı?" is his entry point); (2) Render dashboard: bseu-helpdesk -> Settings -> Build & Deploy -> Auto-Deploy -> "After CI Checks Pass" (my click; until then every push goes live before CI finishes); (3) Phase 8: Claude drafts realistic tickets (long, typos, mixed TR/EN, two problems, personal data, follow-ups) with suggested labels, I decide every label; the gaps to fill are listed in the changelog's "Phase 8" entry. Deploy note: Claude Code's permission check blocks Claude from deploy commands (render/neonctl), even with my OK in chat; the working way is one `!` command that I run (see changelog "Deployment, part 2"). (2026-10-19) Research on real student problems added to docs/problem_catalog.md; capstone wrap-up plan (stages A-D) saved in the changelog, paused by me. Update this line at the end of each session, after asking me.
