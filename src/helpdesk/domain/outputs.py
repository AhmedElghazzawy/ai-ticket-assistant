"""What the model must return, as pydantic schemas. Gemini gets them as its response schema, and
the decision reads them: plain data, so the domain never depends on the AI layer."""

from pydantic import BaseModel, ConfigDict, Field

from helpdesk.domain.tickets import Category, Priority


class Classification(BaseModel):
    """The model's answer for one ticket. `reason` comes first on purpose: think, then decide."""

    model_config = ConfigDict(extra="forbid", strict=True)

    reason: str = Field(
        description="1-2 short sentences in English: which rules from the rulebook apply and why."
    )
    category: Category
    priority: Priority
    escalate: bool


class Answer(BaseModel):
    """The model's grounded answer. `evidence` comes first: quote the rule, then decide, then write."""

    model_config = ConfigDict(extra="forbid", strict=True)

    evidence: str = Field(
        description="The exact sentence(s) copied from the rules that answer the ticket, or an empty string if none do."
    )
    covered: bool = Field(
        description="True only if the rules really answer the student's question."
    )
    reply: str = Field(
        description="A short, polite reply to the student, using only facts from the rules."
    )
    sources: list[str] = Field(
        description="The ids of the rules used (e.g. 'sinavlar.tr#4'); empty if not covered."
    )
