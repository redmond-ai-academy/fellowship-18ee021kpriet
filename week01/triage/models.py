"""The shapes of data in Ticket Triage.

Pydantic gives us two things at once: a JSON schema we can hand to the model,
and a validator we can run on whatever the model sends back. Never trust the
reply until it has passed through `Triage`.
"""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

MAX_SUMMARY_WORDS = 25


class Category(StrEnum):
    BILLING = "billing"
    BUG = "bug"
    HOW_TO = "how_to"
    ACCOUNT_ACCESS = "account_access"
    FEATURE_REQUEST = "feature_request"
    OTHER = "other"


class Priority(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class Triage(BaseModel):
    category: Category
    priority: Priority
    summary: str = Field(description=f"What the customer needs, in at most {MAX_SUMMARY_WORDS} words.")
    needs_human: bool = Field(description="True if a person on the support team must look at this ticket.")
    reason: str = Field(description="One sentence: why this category and this priority.")

    # A JSON schema cannot say "at most 25 words", so we check it ourselves.
    # This is exactly the kind of rule that makes validation worth having.
    @field_validator("summary")
    @classmethod
    def summary_is_short(cls, value: str) -> str:
        words = len(value.split())
        if words > MAX_SUMMARY_WORDS:
            raise ValueError(f"summary has {words} words; the limit is {MAX_SUMMARY_WORDS}")
        return value


class TriageError(Exception):
    """Raised when the model could not give us a valid Triage, even after a retry."""
