"""The one thing the assistant needs from a language model: an answer in a given JSON shape.

Structural (a Protocol), so providers need no shared base class. Gemini implements it today
(ai/gemini.py). Another model only needs this one method; the prompts, the steps and the decision
stay the same, so a model comparison measures the model and nothing else.
"""

from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

# How much the model may think before answering (eval/results_low.json vs results_high.json).
Thinking = Literal["low", "high"]
Output = TypeVar("Output", bound=BaseModel)


class LLMProvider(Protocol):
    @property
    def model(self) -> str:
        """The model's name, recorded with every evaluation result."""
        ...

    def generate_json(
        self, stage: str, system: str, contents: str, schema: type[Output], thinking: Thinking
    ) -> Output:
        """Send `system` (the instructions) and `contents` (the data); return the reply checked
        against `schema`. `stage` names the step in the logs ("classify", "answer")."""
        ...
