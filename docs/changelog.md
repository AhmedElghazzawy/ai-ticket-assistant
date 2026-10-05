# Changelog: everything that happened, and why

The full story of the project, newest step at the bottom. Every new file, change, decision and problem is recorded here, with the reason.

---

## Step 0: Environment (2026-10-06)

### Checks
- Python 3.12.15 and uv 0.12.22 are installed.
- `.env` (the secrets file) already existed and was ignored by git. Claude never reads it.

### Problem found: the old key in git history
- In the first attempt, the key was saved as `key.env` (wrong name, so git did not ignore it). An automatic checkpoint commit (`60b5a4f`) added `key.env` to git.
- Checked with `git ls-remote origin`: GitHub only has `main`. The key **never reached GitHub**.
- The commit still lives in 2 hidden local references (`refs/agents/.../checkpoints/turn/0` and `turn/1`). Deleting them was blocked by the safety system because it cannot be undone.
- Safest fix: create a new API key in Google AI Studio and delete the old one. Then the old key is useless even if it stays in `.git`.

### Files
- `.venv/`: deleted the old one (it still had libraries from the first attempt) and created a fresh, empty one with `uv venv --python 3.12`. A virtual environment is the project's private toolbox of libraries.
- `.gitignore`: replaced GitHub's 220-line template with 5 rules we actually need: `.env` (secrets), `.venv/` (each computer builds its own), `__pycache__/` (Python's automatic cache), `.DS_Store` (macOS junk files), `.claude/settings.local.json` (personal Claude Code permissions).
- `.env.example`: a public template with placeholders only (`GEMINI_API_KEY=your-key-here`, `GEMINI_MODEL=your-model-name-here`). Shows others which settings are needed, without the real values.
- `docs/learning_log.md`: my own notes, one entry per step. Written by me, not by Claude.
- `README.md`: deleted, because it described files from the first attempt that no longer exist. A new one comes in Step 7.
- `claude.md` was renamed to `CLAUDE.md` (the standard name; macOS ignores case, other systems do not).

### Commands and results (in order)
1. `python3.12 --version` -> `Python 3.12.15`. `uv --version` -> `uv 0.12.22`.
2. `ls -la` -> `.env` (69 bytes), `.git`, `.gitignore` (4664 bytes), `.venv`, `README.md`, `claude.md`.
3. `git status --short` -> `?? claude.md` (?? = untracked, git has never saved it).
4. `git check-ignore -v .env` -> `.gitignore:153:.env` (line 153 of .gitignore ignores .env).
5. Read the old `.gitignore`: GitHub's 220-line Python template (Django, Celery, PyCharm...). Line 153 was the only important line for us.
6. `git log --all --oneline -- key.env .env` -> `60b5a4f Agent host session ... baseline checkpoint` (one commit touched a secrets file).
7. `git ls-files` -> only `.gitignore` and `README.md` are tracked. `git remote -v` -> `origin` = github.com/AhmedElghazzawy/ai-ticket-assistant. `git branch -vv` -> `main` is in sync with `origin/main` at `facb85a`.
8. `git show --name-status 60b5a4f -- key.env .env` -> `A key.env` (A = added: the key went into git history).
9. `git for-each-ref --contains 60b5a4f` -> only `refs/agents/.../checkpoints/turn/0` and `turn/1` (hidden local bookmarks made by the old agent tool). `git branch -r --contains 60b5a4f` -> nothing. `git merge-base --is-ancestor 60b5a4f origin/main` -> NO.
10. Old `.venv`: Python 3.12.15, already full of libraries from the first attempt (google-genai, streamlit, altair, pillow, ...).
11. `git ls-remote origin` (asks GitHub what it has) -> only `HEAD` and `refs/heads/main`. Proof the key never reached GitHub.
12. Tried `git update-ref -d` (x2) + `git reflog expire` + `git gc --prune=now` to erase the key commit -> **blocked** by the safety system ("irreversible local destruction"). Left for me to decide.
13. I ran `rm -rf .venv && uv venv --python 3.12` myself and renamed `claude.md` to `CLAUDE.md`. Check: `.venv` has Python 3.12.15 and no packages; 2 checkpoint refs still exist.
14. Wrote `.gitignore`, `.env.example`, `docs/learning_log.md`. `git check-ignore` -> `.env` and `.venv/` ignored; `.env.example` and `docs/learning_log.md` will be tracked.
15. Read the old `README.md` (it described src/app.py, streamlit, requirements.txt, none of which existed), then `rm README.md`.

### Explained along the way
- VS Code colors in the file list come from git: green **U** = untracked (new), yellow **M** = modified, red **D** = deleted, grey = ignored (.env, .venv). After a commit the letters disappear.
- A commit is like a photo of the project; git history keeps every photo, which is why deleting a file does not remove it from old commits.

### Commit
- `2b9bf8b` Clean start: short .gitignore, .env.example, learning log; remove old README

---

## Step 1: First model call (2026-10-06)

### Model choice
- Checked Google's official model list (ai.google.dev/gemini-api/docs/models). The 2.5 models are being limited; Google recommends 3.5 Flash-Lite or 3.8 Flash for new projects.
- Chose `gemini-3.8-flash`: the newest stable model. "Preview" models (like `gemini-3.1-pro-preview`) were avoided because they can change or disappear.
- Free-tier limits are no longer listed in the docs; they are shown per account at aistudio.google.com/rate-limit. Going over the limit returns error `429 RESOURCE_EXHAUSTED`.
- The model name lives in `.env` as `GEMINI_MODEL`, so it can be changed without editing code.

### Libraries
- `google-genai` 2.28.0: Google's official library for calling Gemini.
- `python-dotenv` 1.2.4: reads `.env` so the key never appears in the code.
- Other packages that were installed (tenacity, httpx, ...) are dependencies: helpers those two libraries need.

### Files
- `requirements.txt`: the project's shopping list. Exact versions (`==`) so the code behaves the same on every computer.
- `src/llm.py`: shared Gemini setup, used by every later file.
  - `get_setting()` reads a value from `.env` and stops with a clear message if it is missing (fail fast).
  - `client` is created once, with automatic retries: up to 5 tries in total, waiting 2s, 4s, 8s, 16s (exponential backoff), only for errors that waiting can fix (429 too many requests, 500/503 server errors). Errors like 403 (bad key) or 404 (wrong model name) are not retried.
  - `NO_AFC` switches off automatic function calling (the model calling Python functions). We do not use it, and it printed a confusing warning.
  - `ask(prompt)` sends one prompt and returns the text reply.
- `src/try_one_ticket.py`: a tiny test that sends one ticket and prints the reply.

### Problems we hit
- `GEMINI_MODEL is missing` (twice): `.env` had only the key line, and then the edit was not saved in VS Code. Fixed by adding the line and saving with Cmd+S. Our fail-fast check caught it before any request reached Google.

### What the output taught us
- The reply contained `[Insert Phone Number]`: the model does not know our university's facts. If it guessed, it could invent a fake number (hallucination). This is why the project needs RAG.
- Running the same ticket twice gave two different replies: the model has randomness (temperature). The classifier will use temperature 0.
- A Turkish test reply asked the student for the last 4 digits of their national ID. That rule does not exist: a hallucination and a privacy risk. Replies must be grounded in real documents (Phases 3-4).

### Verification (all passed)
Syntax check; missing setting stops early; wrong model name gives a clear 404 without retries; English ticket answered; Turkish ticket answered in Turkish.

### Commands and results (in order)
1. Read ai.google.dev/gemini-api/docs/models and .../rate-limits (see "Model choice").
2. `uv pip install --python .venv/bin/python google-genai python-dotenv` -> google-genai 2.28.0, python-dotenv 1.2.4, plus their dependencies.
3. Inspected the installed library: `types.HttpRetryOptions` has `attempts` (total tries, including the first; default 5), `initial_delay` (default 1s), `max_delay` (60s), `exp_base` (2.0, each wait doubles), `jitter` (randomness), `http_status_codes`. So retries are built in; no need to write our own loop.
4. Wrote `src/llm.py` in 3 pieces: (1) settings from .env + `get_setting()`, (2) `RETRY` + `client`, (3) `ask()`. Then wrote `src/try_one_ticket.py`.
5. Run 1: `RuntimeError: GEMINI_MODEL is missing`. `.env` had no GEMINI_MODEL line (I added `gemini-3.5-flash-lite` first, then switched to the newest stable `gemini-3.8-flash`).
6. Run 2: same error. `stat .env` (file date and size only, never the content) -> last saved Oct 3, 69 bytes: the edit was not saved in VS Code. After Cmd+S: Oct 6 00:45, 99 bytes.
7. Run 3: worked. A warning appeared first ("Direct use of automatic function calling (AFC)... is not recommended"). Reply was a polite helpdesk answer containing `[Insert Phone Number]`.
8. Checked `types.AutomaticFunctionCallingConfig` -> has a `disable` field. Added `NO_AFC` to `llm.py` and passed `config=NO_AFC` in `ask()`.
9. Run 4: no warning. A different reply to the same ticket (randomness / temperature), again with `[Phone Number]`.
10. Verification: `py_compile` OK; `GEMINI_MODEL= python src/try_one_ticket.py` (empty value for that one command, .env untouched) -> our clear error; `GEMINI_MODEL=gemini-does-not-exist` -> `404 NOT_FOUND`, shown at once, not retried; English ticket -> good reply; Turkish ticket -> good Turkish reply, but it invented a rule asking for the last 4 digits of the national ID.

### Commit
- `ec85425` Step 1: shared Gemini client with retries and a first test call

---

## Step 2: Label definitions (2026-10-06)

### Language decision
- The system is **bilingual (Turkish and English)**. The user picks the language in the app; UI and replies follow that choice. Tickets come in both languages. Every knowledge-base document exists in both languages.
- `docs/labels.md` (the rulebook) is in Turkish. Label IDs (`account_access`, ...), code and comments stay in English, because code needs simple ASCII names.
- Dataset size: Phase 1 = 80 tickets (40 TR + 40 EN). Phase 2 adds 40 locked test tickets (20 + 20). Total 120. Each language needs enough tickets for its own score to mean something.
- Tickets get a new field: `language` (`tr` or `en`).
- CLAUDE.md was updated with all of this.

### Files
- `docs/labels.md`: the label rulebook.
  - 7 categories, each with: what belongs, what does NOT (and where it goes instead), an example, and the responsible unit.
  - Key borders: `account_access` vs `it_support` = "can the student sign in?"; `registration` vs `academic_records` = this semester's course choices vs the official record.
  - Decisions: internship paperwork -> `academic_records`, finding an internship -> `other`; scholarships (including applications) and the dorm fee -> `billing`.
  - Tie-breaker: a ticket with two problems takes the category of the most urgent one. Escalation looks at ALL problems.
  - Golden rule: money between the student and the university goes to `billing`. Other money topics (cafeteria prices) do not.
  - Known limitation (v1): one category per ticket, so a ticket for two offices may partly go to the wrong one.
  - 4 priorities: priority = how much it blocks the student x how soon. An angry tone alone does not raise priority. Priority and escalation are independent.
  - 6 escalation rules (from CLAUDE.md) with Turkish examples. Being upset alone is not a reason.
  - The `escalate` label only follows the 6 rules. Sending `other` tickets to a human is the job of the later decision step, not of the label.

### Gap test
4 tricky tickets were labeled with the rulebook. Two exposed gaps, both fixed:
- "Can't log in + my grade is wrong" -> `account_access`, medium, escalate=true. Gap: the grade dispute goes to the wrong office -> written down as a known limitation.
- "Why is the cafeteria so expensive?!" -> `other`, low, false. Gap: the first golden rule ("all money -> billing") was too broad -> narrowed.

### Final check
Read the whole rulebook again: fixed one contradiction (the `billing` definition still said "any kind of money") and moved the golden rule and limitation under their own heading ("Ek kurallar").

### How the rulebook was built (in order)
1. Claude wrote a first English draft of the 7 categories with 3 open decisions (scholarship application, dorm fee, tie-breaker).
2. I raised internships: they would fall into `other` and always go to a human. Split into paperwork (`academic_records`) vs finding one (`other`). No new category, to keep the design small.
3. I asked for Turkish. Decision (question in the chat): everything users see in Turkish, label IDs and code in English. CLAUDE.md updated. `docs/labels.md` rewritten in Turkish.
4. I then asked for both languages, chosen in the app. Claude recommended Turkish first and English in Phase 7 (less work, cleaner score). I chose both from the start. Decisions (questions in the chat): 80 dev + 40 test tickets; documents in both languages. CLAUDE.md updated in 4 places.
5. Open decisions applied with Claude's recommendations (I said "do what you see is best"): scholarships and dorm fee -> `billing`, tie-breaker = most urgent problem.
6. Priorities and escalation sections written.
7. Gap test with 4 tricky tickets (see "Gap test"). Also labeled: "Yurt ücretini ödedim ama sistem hâlâ borçlu gösteriyor, yarın yurttan çıkarılacağım" -> `billing`, urgent, escalate=true (rule 4); "My laptop got stolen... my saved university email" -> `account_access`, urgent, escalate=true (rule 2).
8. Final read-through: `grep "her türlü"` -> no leftover of the old broad money rule after the fix.

### Commit
- `cad52f7` Step 2: label rulebook in Turkish (categories, priorities, escalation); bilingual plan in CLAUDE.md

---

## Tooling: the "everything file" (2026-10-06)

- `docs/changelog.md` (this file): the story of every change and why. Claude updates it after every change.
- `tools/make_context.py`: builds `claude_context.md`, one file with a teaching note, CLAUDE.md, this changelog and the full content of every project file, ready to paste into a Claude chat. It only includes files git can see, so `.env` is never included.
- `claude_context.md` is in `.gitignore`: it is a generated copy, rebuilt whenever needed.
- CLAUDE.md got a new rule: after every change, update this changelog and rebuild `claude_context.md`.
- First build: 10 files, 30,249 characters. Safety check: every `GEMINI_API_KEY=` line inside is the placeholder `your-key-here`.
- Compared every file in the folder with the bundle. Left out on purpose: `.env` (secret), `claude_context.md` (itself), `src/__pycache__/*.pyc` (Python's automatic machine code), `.claude/settings.local.json` (my Claude Code permissions), `.venv/` (38 MB of other people's libraries; listed in requirements.txt) and `.git/` (described here and in the history section).
- I asked for the full history too. `make_context.py` now also adds, at the end, every commit since the restart (`facb85a`) with every added (+) and removed (-) line, plus all changes not committed yet. The first attempt (before the restart) is left out on purpose so old and new code are not mixed.
- Completeness check: a small script compared every line of every project file with the bundle -> all 10 files and all 488 lines found. Only `claude_context.md` needs to be sent to Claude; the changelog is already inside it.
