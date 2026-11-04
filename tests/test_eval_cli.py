"""Tests for the single eval command: arguments are checked before any paid call is made."""

import pytest

from helpdesk.evals import __main__ as cli
from helpdesk.evals import classifier, pipeline, retrieval, security


def test_defaults_are_the_dev_set_and_high_thinking() -> None:
    args = cli.parse(["classifier"])
    assert (args.suite, args.dataset, args.level) == ("classifier", "dev", "high")


def test_a_locked_set_can_be_chosen() -> None:
    assert cli.parse(["pipeline", "--set", "phase8"]).dataset == "phase8"


@pytest.mark.parametrize(
    "argv",
    [
        ["unknown"],
        ["pipeline", "--set", "nope"],
        ["retrieval", "--set", "dev"],  # retrieval always scores every set
        ["security", "--set", "test"],  # security has its own probes
        ["pipeline", "--level", "low"],  # only the classifier has a thinking-level choice
    ],
)
def test_wrong_arguments_stop_before_any_call(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        cli.parse(argv)


def test_each_suite_runs_its_own_eval(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(classifier, "run", lambda *a: calls.append(("classifier", *a)))
    monkeypatch.setattr(pipeline, "run", lambda *a: calls.append(("pipeline", *a)))
    monkeypatch.setattr(retrieval, "run", lambda: calls.append(("retrieval",)))
    monkeypatch.setattr(security, "run", lambda: calls.append(("security",)))

    cli.main(["classifier", "--level", "low", "--set", "test"])
    cli.main(["pipeline"])
    cli.main(["retrieval"])
    cli.main(["security"])

    assert calls == [
        ("classifier", "low", "test"),
        ("pipeline", "dev"),
        ("retrieval",),
        ("security",),
    ]
