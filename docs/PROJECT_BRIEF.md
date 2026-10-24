# Project brief

The course context, the design decisions and the data rules of the project. Moved here from CLAUDE.md (2026-10-24) so the agent instructions stay short; the text is unchanged. Agents read this file when a task touches labels, data, routing or the professor's requirements.

## What this is
A course project at BŞEÜ (Computer Engineering). The system reads a student's support ticket, labels it (category, priority, escalate), finds the answer in official university documents (RAG), drafts a reply that cites its source, and decides: send it automatically, or hand it to a human together with the draft and the right office.
It is also my FIRST AI engineering project. The goal is for me to learn and truly understand it, not just to have working code.

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

## Repo layout
See ARCHITECTURE.md (current layout and target package layout).

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

## Lessons from my first attempt
- Claude Code ran in auto mode and wrote more than I understood. That is why we restarted.
- The first score of 85% came from a prompt tuned on the same tickets, so it was probably optimistic.
- The secrets file was once named key.env by mistake, so git did not ignore it. The name must be exactly .env.
