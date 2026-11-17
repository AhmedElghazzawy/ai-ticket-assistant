# Product brief

What the system must do, for whom, and the rules its labels, routing and data follow. The design that
implements it is in [ARCHITECTURE.md](../ARCHITECTURE.md); the reasons behind each choice are in
[decisions/](decisions/).

## Problem
Students of Bilecik Şeyh Edebali Üniversitesi (BŞEÜ) send the same questions to many offices: exam
rules, fees, OBS passwords, transcripts. Most answers already exist in official regulations, but are
hard to find; the rest need a person, and reach the wrong office first.

## What the system does
A student writes a ticket in Turkish or English. The system:
1. labels it: category, priority, and whether a person must handle it (escalate);
2. retrieves the matching sections of official university documents (RAG);
3. drafts a reply that uses only those sections and cites them, plus clearly labeled general advice
   for what the documents do not cover;
4. decides in plain code: send the reply automatically, or route the ticket with the draft to the
   responsible office.

Out of scope: acting on student records, answers not backed by an official document, and any
decision only staff may take (grades, exceptions, refunds).

## Labels
Full rulebook (Turkish, also the classifier's prompt): [labels.md](labels.md).

- **Categories (7):** account_access, registration, billing, it_support, academic_records,
  campus_life, other. (No housing: the dorms in Bilecik are run by KYK, the state, not by BŞEÜ.)
- **Priority:** low, medium, high, urgent.
- **Escalate** when any applies: a safety threat, harassment or signs of crisis; a possibly
  compromised account; a policy exception; a money or official-record error that needs a refund or
  correction; a grade or exam dispute, or whether an exam counts; a legal threat, a disciplinary case,
  or repeated contact with no answer. Being upset alone is not a reason.

## Routing (real BŞEÜ offices)
| Category | Office |
|---|---|
| account_access, it_support | Bilgi İşlem Daire Başkanlığı (IT) |
| registration, academic_records | Öğrenci İşleri Daire Başkanlığı (Student Affairs) |
| billing | Öğrenci İşleri, İstatistik Disiplin ve Harçlar Şube Müdürlüğü (fees) |
| campus_life | Sağlık, Kültür ve Spor (SKS) Daire Başkanlığı |
| other | Student Affairs duty staff |

System names used in tickets and documents: OBS (student system), SOFRA (passwords and student
e-mail), @ogrenci.bilecik.edu.tr, UZEM at ders.bilecik.edu.tr, Akıllı Kart (student ID card). See
[problem_catalog.md](problem_catalog.md).

## When a reply is sent automatically
Only if every check passes (`src/helpdesk/domain/decision.py`, tested in `tests/test_decision.py`):
the category is not `other`; the model did not escalate; the priority is not `urgent`; retrieval found
a strong match; the documents answer the main question; the reply cites a retrieved section; and its
quoted evidence really appears in that section. Otherwise the ticket goes to the office with the draft.

## Data rules
- **Bilingual:** the student picks Turkish or English, and everything they see is in that language.
  Every knowledge-base document exists in both. Label ids, code and comments are English (ASCII).
- **Datasets** (`data/tickets/`, one JSON object per line: id, text, language, category, priority,
  escalate):
  - `tickets.jsonl`: 80 dev tickets (40 TR + 40 EN). Prompts are developed on these.
  - `test_tickets.jsonl`: 40 tickets, **locked** (ADR 0003): only final scores, never prompt tuning.
  - `realistic_tickets.jsonl`: 40 realistic tickets (typos, mixed languages, several issues), **locked**.
  - `expected_docs.jsonl`: for every ticket, the document that answers it, or none (retrieval eval).
- **Labels are human decisions:** an LLM may draft candidate tickets; the maintainer labels every one.
  The datasets are synthetic, written from real BŞEÜ systems and common student problems, and
  labelled by one person; scores are reported with that limit.
- **Privacy:** student messages are personal data. Ticket text and e-mail addresses never go into
  logs, and real tickets are never committed.
