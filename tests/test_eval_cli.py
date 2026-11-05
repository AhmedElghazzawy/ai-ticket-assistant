"""Tests for the single eval command: arguments are checked before any paid call is made."""

import pytest

from helpdesk.evals import __main__ as cli
from helpdesk.evals import classifier, pipeline, retrieval, security


def test_defaults_are_the_dev_set_and_high_thinking() -> None:
    args = cli.parse(["classifier"])
    assert (args.suite, args.dataset, args.level) == ("classifier", "dev", "high")
    assert (args.model, args.runs) == (None, classifier.RUNS)  # the model from the settings


def test_another_model_can_be_compared() -> None:
    args = cli.parse(["classifier", "--model", "gemini-3.6-flash", "--runs", "1"])
    assert (args.model, args.runs) == ("gemini-3.6-flash", 1)


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
        ["pipeline", "--model", "gemini-3.6-flash"],  # the model comparison is the classifier's
        ["classifier", "--runs", "0"],
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

    cli.main(["classifier", "--level", "low", "--set", "test", "--model", "m", "--runs", "1"])
    cli.main(["pipeline"])
    cli.main(["retrieval"])
    cli.main(["security"])

    assert calls == [
        ("classifier", "low", "test", "m", 1),
        ("pipeline", "dev"),
        ("retrieval",),
        ("security",),
    ]


def test_each_compared_model_gets_its_own_result_file() -> None:
    # Comparing models must never overwrite the main model's saved scores.
    assert classifier.result_path("high", "dev", None).name == "results_high.json"
    assert classifier.result_path("high", "phase8", None).name == "results_high_phase8.json"
    assert classifier.result_path("high", "dev", "gemini-3.6-flash").name == (
        "results_high_gemini-3.6-flash.json"
    )
