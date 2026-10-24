---
name: run-evals
description: Run a classifier, retrieval, pipeline or security evaluation with real Gemini calls - choosing the dataset safely, respecting rate limits, never tuning on locked sets, and reporting sample sizes and 95% intervals.
---

# Run evals

Evals make real, paid Gemini calls. Run one only when the user asks, and say how many calls it makes.

## Datasets
| Name | File | Use |
|---|---|---|
| dev | data/tickets/tickets.jsonl | Tuning prompts and reading mistakes |
| test | data/tickets/test_tickets.jsonl | LOCKED: final score only, never tune on it |
| phase8 | data/tickets/phase8_tickets.jsonl | LOCKED realistic set: final score only |

Never change a prompt, a rule or a threshold after looking at locked-set results (ADR 0003). If a locked
run shows a problem, write it down; fixing it needs NEW tickets to measure the fix.

## Commands
| Eval | Command | Calls |
|---|---|---|
| Classifier | `uv run python src/evaluate.py high [test\|phase8]` | 2 runs per ticket |
| Retrieval (hit@3) | `uv run python src/evaluate_retrieval.py` | embeddings only, every set |
| Pipeline (unsafe auto-sends) | `uv run python src/evaluate_pipeline.py [test\|phase8]` | 2 per ticket |
| Prompt injection | `uv run python src/evaluate_security.py` | 12 probes |

The scripts already wait between calls and retry on 429; never wrap them in a faster loop.

## Reporting
- Every number with its sample size and the Wilson 95% interval (`src/stats.py`), e.g.
  "72.5% (57-84%, n=40)".
- Missed escalations first: they are the most dangerous error.
- Compare with the previous saved result in `eval/` and say whether the difference is larger than the
  interval. Two runs that differ inside the interval are noise (temperature is 1.0).
- Say which prompt version produced the result. Results are files in `eval/`, committed with the change
  that produced them.
- For a deeper reading, the `eval-analyst` subagent can review the saved JSON.

## Record
docs/changelog.md: command, dataset, number of calls, errors, results with intervals, what changed and
what it does NOT prove. Update README and docs/ROADMAP.md numbers only from a saved result file.
