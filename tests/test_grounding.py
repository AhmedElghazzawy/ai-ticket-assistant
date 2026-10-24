"""Tests for the evidence check: no AI calls, only hand-made quotes."""

from helpdesk.domain.grounding import is_grounded

RULES = [
    (
        "Kayıt sildirince iade\nKayıt yaptırıp kendi isteğiyle kaydını sildiren öğrencilerin "
        "katkı payı ve öğrenim ücretleri geri ödenmemektedir."
    ),
    "Bütünleme\nBütünleme sınavına girmek için ayrıca başvuru gerekmez.",
]


def test_exact_quote_is_grounded() -> None:
    assert is_grounded("Bütünleme sınavına girmek için ayrıca başvuru gerekmez.", RULES)


def test_formatting_differences_do_not_matter() -> None:
    # The model may change case, quotes, spacing, add the rule id or join quotes with "...".
    evidence = (
        '[harc_ucretler.tr#5] "Kayıt yaptırıp kendi isteğiyle kaydını sildiren öğrencilerin\n'
        'katkı payı ve öğrenim ücretleri geri ödenmemektedir" ... BÜTÜNLEME sınavına girmek '
        "için ayrıca başvuru gerekmez"
    )
    assert is_grounded(evidence, RULES)


def test_separately_quoted_sentences_are_checked_one_by_one() -> None:
    # Bug found in the dev run (tr-007): two real sentences, each in its own quotes, from
    # different places in the rules. The quote after the period hid the sentence end.
    evidence = (
        '"Bütünleme sınavına girmek için ayrıca başvuru gerekmez." '
        "“Kayıt yaptırıp kendi isteğiyle kaydını sildiren öğrencilerin katkı payı ve öğrenim "
        "ücretleri geri ödenmemektedir.”"
    )
    assert is_grounded(evidence, list(reversed(RULES)))


def test_quote_from_the_ticket_instead_of_the_rules_is_not_grounded() -> None:
    # Prompt injection: the ticket carried its own fake rule, and the model "quoted" it.
    fake = "Kaydını sildiren öğrencilere harç ücreti her zaman tam olarak iade edilir."
    assert not is_grounded(fake, RULES)


def test_one_invented_sentence_among_real_ones_is_not_grounded() -> None:
    evidence = (
        "Bütünleme sınavına girmek için ayrıca başvuru gerekmez. "
        "Bütünleme notu ortalamaya iki kat etki eder."
    )
    assert not is_grounded(evidence, RULES)


def test_paraphrase_is_not_grounded() -> None:
    assert not is_grounded("Bütünlemeye girmek için başvuru yapmanız gerekmez.", RULES)


def test_empty_evidence_is_not_grounded() -> None:
    assert not is_grounded("", RULES)
    assert not is_grounded("Evet.", RULES)  # too short to prove anything
