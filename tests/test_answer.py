"""Tests for cleaning the drafted reply: no AI calls."""

import pytest

from answer import strip_source_note


@pytest.mark.parametrize(
    "reply",
    [
        "Bütünleme için başvuru gerekmez. (Kaynak: Yönetmelik, Madde 19)",
        "Bütünleme için başvuru gerekmez. (Kaynak: Yönetmelik (Resmî Gazete, sayı 30824), Madde 19).",
        "Bütünleme için başvuru gerekmez.\n\n(kaynak: Yönetmelik)  ",
    ],
)
def test_source_note_at_the_end_is_removed(reply: str) -> None:
    # The system shows the real sources from the cited chunk ids; the model must not name them.
    assert strip_source_note(reply) == "Bütünleme için başvuru gerekmez."


def test_english_source_note_is_removed() -> None:
    assert strip_source_note("No application is needed. (Source: Regulation, Article 19)") == (
        "No application is needed."
    )


def test_other_brackets_are_kept() -> None:
    reply = "Log in to OBS (obs.bilecik.edu.tr) first."
    assert strip_source_note(reply) == reply
