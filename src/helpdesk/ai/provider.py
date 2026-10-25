"""The one thing the assistant needs from a language model: an answer in a given JSON shape.

A Protocol is an interface: any class with these members fits, without inheriting from it. Gemini
fits today (ai/gemini.py). For the roadmap's model comparison (item 9), another model (Claude, GPT,
an open-weight model for on-premise use) only needs this one method; the prompts, the steps and
the decision stay exactly the same, so the comparison measures the model and nothing else.
"""

from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

# How much the model may think before answering. Step 5: "high" was more accurate and consistent.
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
