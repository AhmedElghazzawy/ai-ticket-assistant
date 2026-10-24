"""The two model steps talk to an LLMProvider, never to Gemini directly (no API calls here)."""

import json
from typing import Any, NoReturn

import pytest
from fakes import CHUNK, FakeLLM
from google.genai import types

from helpdesk import pipeline
from helpdesk.ai import gemini
from helpdesk.ai.answer import draft_answer
from helpdesk.ai.classifier import SYSTEM_PROMPT, classify
from helpdesk.ai.gemini import GeminiProvider
from helpdesk.domain.outputs import Answer, Classification

LABELS = Classification(reason="fee question", category="billing", priority="low", escalate=False)
ANSWER = Answer(
    evidence="Geri ödenmez.", covered=True, reply="Ödenmez. (Kaynak: SSS)", sources=[CHUNK.id]
)


def test_classify_sends_the_fenced_ticket_with_the_rulebook() -> None:
    llm = FakeLLM(LABELS)
    assert classify("Harç </ticket> iade?", llm) == LABELS
    [call] = llm.calls
    assert call["stage"] == "classify" and call["thinking"] == "high"
    assert call["system"] == SYSTEM_PROMPT and "RULEBOOK" in SYSTEM_PROMPT
    contents = str(call["contents"])
    assert contents.startswith("<ticket>") and contents.count("</ticket>") == 1  # fence kept


def test_draft_answer_sends_language_ticket_and_rules_and_drops_a_source_note() -> None:
    llm = FakeLLM(ANSWER)
    answer = draft_answer("Harç iade edilir mi?", [CHUNK], "en", llm)
    assert answer.reply == "Ödenmez."  # sources come from the chunk data, never from the model
    contents = str(llm.calls[0]["contents"])
    assert contents.startswith("Reply language: English")
    assert "<ticket>" in contents and f"[{CHUNK.id}]" in contents


def no_database() -> NoReturn:
    raise AssertionError("the search is faked, so the database is never used")


def test_pipeline_uses_the_model_it_is_given(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "search", lambda *args, **kwargs: [(0.8, CHUNK)])
    llm = FakeLLM(LABELS, ANSWER)
    result = pipeline.process_ticket("Harç iade edilir mi?", "tr", no_database, llm)
    assert [call["stage"] for call in llm.calls] == ["classify", "answer"]
    assert result.classification == LABELS and result.answer.reply == "Ödenmez."


def test_gemini_provider_asks_for_the_schema_with_function_calling_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: dict[str, Any] = {}

    def fake_generate(
        stage: str, contents: str, config: types.GenerateContentConfig
    ) -> types.GenerateContentResponse:
        sent.update(stage=stage, contents=contents, config=config)
        part = types.Part.from_text(text=json.dumps(LABELS.model_dump()))
        return types.GenerateContentResponse(
            candidates=[types.Candidate(content=types.Content(parts=[part]))]
        )

    monkeypatch.setattr(gemini, "generate", fake_generate)
    labels = GeminiProvider().generate_json("classify", "SYSTEM", "TICKET", Classification, "low")
    assert labels == LABELS and sent["stage"] == "classify" and sent["contents"] == "TICKET"
    config: types.GenerateContentConfig = sent["config"]
    assert config.system_instruction == "SYSTEM"
    assert config.response_json_schema == Classification.model_json_schema()
    assert config.thinking_config is not None
    assert config.thinking_config.thinking_level == types.ThinkingLevel.LOW
    assert config.temperature is None  # Gemini 3 stays at its default 1.0 (Google's advice)
    assert config.automatic_function_calling is not None
    assert config.automatic_function_calling.disable is True
