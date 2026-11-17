# Changelog

Notable changes per release, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Every individual change, with its reason and measured result, is in the engineering journal
[docs/dev-notes/journal.md](docs/dev-notes/journal.md).

## [Unreleased]

### Changed
- **README:** a one-line pitch, a "Design decisions" table (why no LangChain, plain-code decisions,
  code-checked citations, pgvector, locked sets, the model chain), results dated by the system version
  they measured, and a coverage badge fed by CI (no third-party service).
- Issue forms, a pull-request template, private vulnerability reporting switched on (SECURITY.md
  pointed to it), and the branch + pull-request workflow in CONTRIBUTING.md.
- **Docs read as a product, not a course:** the product brief and the roadmap describe the system
  and its milestones; the engineering journal moved to `docs/dev-notes/journal.md`; `CLAUDE.md` holds
  only agent and contributor guidance.
- The second locked set is now `realistic` (`SET=realistic`); its content is byte-identical
  (SHA-256 checked), and a test fails if any locked dataset is not guarded.
- Code comments explain why; tutorial-style and phase-numbered comments were rewritten.
- **Faster, steadier live answers:** a chain of three free Gemini models replaces the single backup;
  a busy model hands over at once, a slow one is raced after 9 s, nobody waits past 25 s, and the
  question's embedding has an 8 s limit (ADR 0018, replaces 0014 and 0015).

### Added
- **"Send to a specialist"**: a student can send an automatic answer on to the right office with one
  click; staff see it marked, Insights count it (ADR 0016).
- **Ticket history**: an append-only audit trail of who created, moved, requested or answered each
  ticket, written in the same SQL statement as the change and protected by a database trigger;
  a History timeline on the staff ticket page (ADR 0017).
- **Use-case layer** (`services/`) and an architecture test that fails CI if a layer imports one
  above it; SQL now lives only in `storage/`.
- Direct answers plus labeled general help when the documents do not answer (ADR 0013).
- Backup Gemini model on overload or timeout for the live API, with a circuit breaker (ADR 0014, 0015).
- Prompt-injection defence: fenced tickets and evidence checked in code; 12/12 attack probes safe
  (ADR 0010).
- Students follow their tickets and read staff replies on "Taleplerim" with a secret code (ADR 0009);
  feedback buttons; the "Nasıl karar verildi?" decision trace; the staff Insights page.
- First help on forwarded tickets: the cited part of the draft, never on escalated tickets (ADR 0008).
- Knowledge base grown to 28 documents (190 chunks), including grades and GPA.
- One-command versioned evals (`make eval`) with Wilson 95% intervals; a second locked realistic test
  set (40 tickets).
- English README with a Turkish twin, MIT license, Playwright tests on desktop and phone.

### Changed
- Package restructured into layers with an app factory, typed settings and an `LLMProvider`
  protocol (ADR 0012).
- Live main model `gemini-3.1-flash-lite`, chosen by measurement on the dev set (ADR 0015).

### Removed
- The old Streamlit panel and its dependencies (replaced by the React staff console).

## [0.9] - 2026-10-16

First complete version and live demo: classification (7 categories, 4 priorities, escalation),
retrieval over official BŞEÜ documents with pgvector, a cited draft reply, and a plain-code decision
to auto-send or route to the office. Student chat and staff console, demo mode, CI, Docker.
Locked test set (n=40): all three labels right 73.8% (about 60-86%), 0 of 14 escalations missed.

[Unreleased]: https://github.com/AhmedElghazzawy/ai-ticket-assistant/compare/v0.9...HEAD
[0.9]: https://github.com/AhmedElghazzawy/ai-ticket-assistant/releases/tag/v0.9
