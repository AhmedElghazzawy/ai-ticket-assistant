---
name: new-adr
description: Write an Architecture Decision Record in docs/decisions/ (Turkish, numbered, with context, decision, consequences, alternatives) whenever a significant design or technology choice is made or reversed.
---

# New decision record (ADR)

Write one when a choice would make a reviewer ask "why this way?": a new library or service, a rule
that changes results, a security trade-off, a data or hosting decision, or reversing an earlier ADR.

## Steps
1. Next number: the highest `docs/decisions/NNNN-*.md` plus one, four digits.
2. File name: `NNNN-short-kebab-title.md` (English slug, ASCII).
3. Write it in Turkish, English technical terms kept as they are. Template:

```markdown
# NNNN: <Karar başlığı>

**Durum:** Kabul edildi (YYYY-MM-DD).

## Bağlam
<What problem, which constraints, what was measured. Numbers with sample sizes.>

## Karar
<What we do, precisely enough to check in code. Name the files.>

## Sonuçlar
<What gets better, what gets worse, what it does NOT solve. Honest limits.>

## Alternatifler
- <Option>: <why not, in one or two sentences>.
```

4. Add a row to the table in `docs/decisions/README.md`.
5. If it replaces an older ADR, do not delete the old one: set its status to `Yerini aldı: NNNN`.
6. Link the ADR from the code that implements it (a short comment) and from ARCHITECTURE.md if it
   changes the architecture.
7. Mention it in docs/changelog.md.
