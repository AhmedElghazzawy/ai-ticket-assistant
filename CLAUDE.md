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
  7. Ask me to write 3-5 lines in my own words in docs/learning_log.md. I write them, you only prompt me.
  8. Suggest a commit message. Only commit or push when I say so.
- Do not add libraries, files or features I did not ask for. Add a library only when the current step needs it, and tell me why. Simple but impressive, no over-engineering.
- Keep code short and readable: small functions, type hints, short English comments, snake_case names.
- Tell me honestly when something is weak or may be misleading (for example an inflated score), even if I did not ask.
- If I say "I don't understand", explain it another way (analogy, tiny example) before moving on.

## Safety rules
- Never read, print, copy or commit .env. It holds my API key. The file must be named exactly .env and be listed in .gitignore.
- Keep a .env.example that contains only placeholders (GEMINI_API_KEY=your-key-here, GEMINI_MODEL=...). If .env does not exist, ask me to create it, and never ask me to paste the key into the chat.
- Check the current Gemini model names and free-tier limits in Google's official docs instead of assuming. The model name lives in .env as GEMINI_MODEL, so it can change without editing code.
- The free tier has request limits per minute. Add short waits between calls and automatic retries, and never loop over many tickets without that.
- Never commit or push without asking me first.

## What my professor asked for (his feedback on my idea)
He said the idea is feasible but too general. Before building, I must define clearly:
- which kinds of tickets, which units handle them, and what the results are
- how many ticket categories, and which ones
- which data and which documents the retrieval (RAG) part uses
- how the system will be evaluated
- the scope and limits
He also said these parts can be explained separately: classification, RAG retrieval, answer generation, and the forward / do-not-forward decision. His suggested flow: user submits ticket, system classifies it, RAG retrieves information from the knowledge base, a draft answer is created, the system decides on automatic reply, and unresolved or special cases go to the relevant unit or person.

## Project design (decided)
Categories (7): account_access, registration, billing, it_support, academic_records, housing, other
Priority: low, medium, high, urgent
Escalate to a human when ANY applies: safety threat, harassment, or signs of crisis; account possibly compromised; the student needs a policy exception; a money dispute needing a refund or correction; a grade or exam dispute; a legal threat or repeated contact with no answer. Being upset alone is NOT a reason.
Routing to units: account_access and it_support go to the IT Department; registration and academic_records go to Student Affairs; billing goes to the Finance Office; housing goes to the Housing Office; other goes to Student Affairs duty staff.

Pipeline (target): ticket -> classify -> retrieve document chunks -> draft reply that cites its source -> decide -> auto-send or route to a unit.
Auto-send only if ALL pass: category is not "other"; the model did not ask to escalate; retrieval found a strong match; the draft cites a source. Otherwise escalate.

## Data rules
- Language: the system is bilingual, Turkish and English. The user picks the language in the app, and everything they see (UI text, draft replies) is in that language. Tickets come in both languages, and every knowledge-base document exists in both Turkish and English. docs/labels.md (the label rulebook) is in Turkish. Label IDs (account_access, ...), code and comments stay in English, because code needs simple ASCII names.
- I write and label the tickets myself. You may suggest tickets that cover gaps (edge cases, tricky wording), but the final labels are my decision. Discuss each label with me and explain why.
- Format: data/tickets/tickets.jsonl, one JSON object per line: id, text, language (tr or en), category, priority, escalate.
- Phase 1 has about 80 tickets (40 Turkish + 40 English) and no more. Phase 2 adds about 40 more (20 + 20), and those 40 are a LOCKED TEST SET: never used to adjust the prompt, only for the final score. Never tune the prompt on the test set.

## Tech stack (introduced one at a time, when needed)
Python 3.12 with a virtual environment in .venv (use uv if it is installed, otherwise ask me), google-genai, python-dotenv, pydantic, Streamlit and pandas for a small web page, later pgvector (Postgres), FastAPI, LangGraph, pytest.

## Repo layout (target)
data/tickets/, data/knowledge_base/, src/, eval/, docs/ (learning_log.md), README.md, CLAUDE.md, requirements.txt, .env.example, .gitignore

## Phase 1: rebuild from zero, understanding every step
Everything was deleted on purpose so I can rebuild it slowly. Do NOT recreate the old code from memory or paste big files. Build it with me, step by step, using the teaching mode above.
- Step 0: Environment. Check Python 3.12, the virtual environment, .gitignore, .env.example, requirements.txt. Help me create .env without ever reading it. Explain what each file is for.
- Step 1: First model call. Create src/llm.py (shared Gemini setup: key from .env, model name from GEMINI_MODEL, automatic retries) and a tiny test script that sends one ticket and prints the reply. Explain what an API call is.
- Step 2: Define the labels together. Before any code, we write the category definitions, priority definitions and escalation rules in plain words. I write them, you check them for overlaps and gaps.
- Step 3: The data. src/tickets.py defines what a valid ticket is (pydantic model, Literal types for category and priority) and loads tickets.jsonl with clear errors. I write the first 20 tickets with you; we reach about 80 (half Turkish, half English) with a good mix in each language: every category, every priority, edge cases, and about a quarter that need escalation.
- Step 4: The classifier. src/classifier.py: the system prompt built from our definitions, structured output (response schema), temperature 0, and the "reason" field first. Explain why each choice matters. Run it on the tickets and read every mistake together.
- Step 5: The evaluation. src/evaluate.py: score per label and overall, and missed escalations (the most dangerous error: a ticket that needed a human but was not escalated). Save the run to eval/results.json. Explain what the score does and does not prove.
- Step 6: A small web page. src/app.py with Streamlit: try one ticket, browse the dataset, run the evaluation. Keep it small and explain it block by block.
- Step 7: Review and package. I explain the whole flow back in my own words, we write a short README, and prepare what I show my professor (in Turkish): the categories and units table, the dataset description, the evaluation method and the first score.

Phase 1 is done when:
- I can explain every file in my own words.
- I wrote the labels and agree with them.
- I understand what the first score means and what it does NOT prove (the prompt was adjusted while looking at the same tickets, so the number is optimistic until Phase 2's locked test set).
- Everything is committed and pushed, and the docs/learning_log.md has an entry for each step.

## Later phases (one deliverable per week for my professor)
2. Week 3: trustworthy score. About 120 tickets total, 40 locked as the test set, compare dev score and test score for each language, read every mistake.
3. Weeks 4-5: knowledge base of 8-10 short policy documents, each in Turkish and English, chunking, embeddings, retrieval. In-memory search first, then pgvector. Measure how often the right document is in the top 3.
4. Week 6: grounded draft replies that cite their source, the decision function, routing to units. Rate 15 drafts; count tickets auto-sent that should not have been.
5. Week 7: FastAPI endpoint POST /tickets, saved results, pytest tests for the decision rules.
6. Week 8: rebuild as a LangGraph graph, add a human review queue tab in Streamlit.
7. Week 9: stress tests (ambiguous tickets, two problems in one ticket, empty text, prompt injection), then ONE final evaluation on the locked test set.
8. Week 10: README, architecture diagram, Turkish project report, 5-minute demo script, v1.0 tag.

## Lessons from my first attempt
- Claude Code ran in auto mode and wrote more than I understood. That is why we restarted.
- The first score of 85% came from a prompt tuned on the same tickets, so it was probably optimistic.
- The secrets file was once named key.env by mistake, so git did not ignore it. The name must be exactly .env.

## Current status
Phase 1, Step 0 not started. Everything was deleted on purpose. Update this line at the end of each session, after asking me.
