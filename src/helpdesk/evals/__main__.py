"""One command for every eval. Each result in eval/ records what produced it (evals/report.py).

Run: make eval SUITE=classifier|pipeline|retrieval|security [SET=dev|test|phase8] [LEVEL=low|high]
     [MODEL=gemini-...] [RUNS=1|2]   (classifier only: compare another model; own result file)
(or: uv run python -m helpdesk.evals classifier --model gemini-3.6-flash --runs 1)

Evals make real model calls: see .claude/skills/run-evals/SKILL.md before running one.
"""

import argparse
from collections.abc import Sequence

from helpdesk.ai.classifier import THINKING
from helpdesk.domain.tickets import DATASETS
from helpdesk.evals import classifier, pipeline, retrieval, security

SUITES = ("classifier", "pipeline", "retrieval", "security")
PER_DATASET = ("classifier", "pipeline")  # retrieval scores every set; security has its own probes


def parse(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Check the arguments before any paid call is made."""
    parser = argparse.ArgumentParser(prog="python -m helpdesk.evals", description=__doc__)
    parser.add_argument("suite", choices=SUITES)
    parser.add_argument("--set", dest="dataset", choices=list(DATASETS))
    parser.add_argument("--level", choices=("low", "high"))
    parser.add_argument("--model", help="classifier only: another model than GEMINI_MODEL")
    parser.add_argument("--runs", type=int, help="classifier only: how often each ticket is asked")
    args = parser.parse_args(argv)
    if args.dataset and args.suite not in PER_DATASET:
        parser.error(f"{args.suite} always runs on its own data; drop --set")
    for option in ("level", "model", "runs"):
        if getattr(args, option) is not None and args.suite != "classifier":
            parser.error(f"--{option} only applies to the classifier")
    if args.runs is not None and args.runs < 1:
        parser.error("--runs must be at least 1")
    args.dataset = args.dataset or "dev"
    args.level = args.level or THINKING
    args.runs = args.runs or classifier.RUNS
    return args


def main(argv: Sequence[str] | None = None) -> None:
    args = parse(argv)
    if args.suite == "classifier":
        classifier.run(args.level, args.dataset, args.model, args.runs)
    elif args.suite == "pipeline":
        pipeline.run(args.dataset)
    elif args.suite == "retrieval":
        retrieval.run()
    else:
        security.run()


if __name__ == "__main__":
    main()
