"""Check in plain code that the model's quoted evidence really comes from the retrieved rules.

The model is asked to COPY the rule sentences into `evidence`. If a ticket smuggles in fake
"rules" (prompt injection) or the model invents one, the quote is not found in the documents,
and the decision must not trust the reply (domain/decision.py)."""

import re
import unicodedata

# A rule id the model may put in front of a quote, e.g. "[sinavlar.tr#4]".
CHUNK_ID = re.compile(r"\[[\w.]+#\d+\]")
# Where one quoted piece ends and the next begins: a line break, an ellipsis, or a sentence end
# (which may be followed by a closing quote: `gerekmez." "Kayıt`).
PIECE_BREAK = re.compile(r"\n+|\.\.\.|…|(?<=[.!?;:])[\"'”’»]?\s+")
QUOTES = str.maketrans({"“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "«": '"', "»": '"'})
MIN_WORDS = 3  # shorter pieces ("Evet.", "Madde 19") prove nothing either way


def normalize(text: str) -> str:
    """Compare text, not formatting: same Unicode form, straight quotes, lower case, single spaces."""
    text = unicodedata.normalize("NFKC", text).translate(QUOTES).casefold()
    return " ".join(text.split())


def pieces(evidence: str) -> list[str]:
    """The quoted pieces worth checking, without ids, outer quotes and end punctuation."""
    found = []
    for piece in PIECE_BREAK.split(CHUNK_ID.sub(" ", evidence)):
        piece = normalize(piece).strip(" \"'-*•").rstrip(".!?;:,")
        if len(piece.split()) >= MIN_WORDS:
            found.append(piece)
    return found


def is_grounded(evidence: str, rule_texts: list[str]) -> bool:
    """True if there is evidence and every piece of it appears word for word in the rules."""
    quoted = pieces(evidence)
    rules = normalize("\n".join(rule_texts))
    return bool(quoted) and all(piece in rules for piece in quoted)
