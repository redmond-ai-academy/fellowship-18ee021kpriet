"""A thin wrapper around the model, so the rest of the code never imports the SDK.

Why a wrapper? Two reasons:
  1. Tests must run with no network and no key. `FakeClient` stands in for the model.
  2. If the SDK or the model changes, only this file changes.

Everything here is provided. Read it, because you will debug through it.
"""

import json
import os
from dataclasses import dataclass
from typing import Protocol, Sequence

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

# Free-tier model from Google's quickstart (checked 13 October 2026).
# Models get retired, so GEMINI_MODEL in .env can override this without a code change.
DEFAULT_MODEL = "gemini-3.8-flash"


class ModelCallError(RuntimeError):
    """The model could not be reached (no key, no network, rate limit...).

    Different from TriageError: here we never got an answer to validate.
    """


class ModelClient(Protocol):
    """Anything that can turn (instructions, input, schema) into raw JSON text."""

    model_name: str

    def generate_json(self, system: str, user: str, schema: type[BaseModel], temperature: float) -> str:
        """Return the model's reply as raw text. Not parsed, not validated."""
        ...


class GeminiClient:
    """Calls the Gemini API with structured output."""

    def __init__(self, model: str | None = None) -> None:
        # utf-8-sig so a .env saved by Notepad with a BOM still works on Windows.
        load_dotenv(encoding="utf-8-sig")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ModelCallError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env, paste your key after the = sign, "
                "and run again. (Try --fake to see the table without a key.)"
            )
        self.model_name = model or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
        self._client = genai.Client(api_key=api_key)

    def generate_json(self, system: str, user: str, schema: type[BaseModel], temperature: float) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            # Structured output: the model is constrained to JSON that matches the schema.
            response_mime_type="application/json",
            response_schema=schema,
        )
        try:
            response = self._client.models.generate_content(model=self.model_name, contents=user, config=config)
        except genai_errors.APIError as exc:
            raise ModelCallError(f"Gemini API error {exc.code}: {exc.message}") from exc
        # .text is None if the reply was blocked or empty. Return "" and let validation catch it.
        return response.text or ""


@dataclass
class FakeCall:
    """What the code under test sent to the model. Tests can inspect these."""

    system: str
    user: str
    schema: type[BaseModel]
    temperature: float


class FakeClient:
    """Plays back scripted replies, in order. For tests: no network, no key, no surprises."""

    model_name = "fake-model"

    def __init__(self, responses: Sequence[str]) -> None:
        self._responses = list(responses)
        self.calls: list[FakeCall] = []

    def generate_json(self, system: str, user: str, schema: type[BaseModel], temperature: float) -> str:
        self.calls.append(FakeCall(system, user, schema, temperature))
        if len(self.calls) > len(self._responses):
            raise AssertionError(
                f"FakeClient was called {len(self.calls)} times but only {len(self._responses)} replies were scripted."
            )
        return self._responses[len(self.calls) - 1]


# --- Demo mode -------------------------------------------------------------------------------
# A crude keyword guesser, not an AI. `run.py --fake` uses it so you can see the whole pipeline
# (table, accuracy, traces) before you have an API key. Expect it to get some tickets wrong.

_DEMO_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("account_access", ("locked out", "otp", "password", "log in", "login", "someone else")),
    ("feature_request", ("please add", "would love", "feature", "wish you had")),
    ("how_to", ("how do i", "how can i", "where do i", "how to")),
    ("billing", ("charged", "refund", "payment of", "subscription")),
    ("bug", ("error", "wrong", "not working", "slow", "failed", "shows")),
]


class DemoClient:
    model_name = "demo-keyword-guesser"

    def generate_json(self, system: str, user: str, schema: type[BaseModel], temperature: float) -> str:
        text = user.lower()
        category = next((name for name, words in _DEMO_RULES if any(w in text for w in words)), "other")
        urgent = any(w in text for w in ("urgent", "tomorrow", "twice", "all my", "since this morning"))
        priority = "P2" if urgent else ("P4" if category in ("how_to", "feature_request", "other") else "P3")
        body = user.split("<ticket>")[-1].split("</ticket>")[0].strip()
        summary = " ".join(body.split()[:20])
        return json.dumps(
            {
                "category": category,
                "priority": priority,
                "summary": summary,
                "needs_human": priority in ("P1", "P2"),
                "reason": f"Keyword match on '{category}' (demo mode, not a real model).",
            }
        )
