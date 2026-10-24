---
name: db-migration
description: Change the Postgres schema safely by appending a numbered step to MIGRATIONS in src/store.py - never editing a released step - with a test that upgrades an existing database.
---

# Database migration

`src/store.py` holds `MIGRATIONS: dict[int, str]`. On startup `migrate()` runs every step above the
stored version, all pending steps in one transaction under an advisory lock (safe when two instances
start at once). Production (Neon) holds real data: a wrong step loses it.

## Rules
- Append a new number. Never edit, reorder or delete a released step, even to fix a typo: add a step.
- Keep a step small: no step that rewrites the whole tickets table while the app serves traffic.
- Adding a column to a table that has rows: give it a DEFAULT or make it NULL-able, or the step fails.
- Personal data (student text, e-mails) only in columns that already hold it; tokens and codes are
  stored as hashes (see `token_hash`), never in plain text.
- Indexes for new query patterns; pgvector columns use the same dimensions as `retrieval.DIMENSIONS`.

## Steps
1. Test first in `tests/test_store.py`: the new behaviour on a fresh schema, and that a database at the
   previous version upgrades without losing a ticket.
2. Append the step; update the pydantic models (`StoredTicket` and friends) and the queries.
3. Run the `quality-gate` skill. Tests run every migration on a fresh schema each time.
4. If the API response changes, follow the `add-api-endpoint` skill to regenerate the client.
5. changelog entry, naming the new schema version. Remind the user that the live database upgrades on
   the next deploy, and that a step cannot be undone there without a new step.
