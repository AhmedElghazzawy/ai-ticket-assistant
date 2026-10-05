"""Shared Gemini setup: settings from .env, one client, and ask() with retries."""

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # read .env and turn each line into an environment variable


def get_setting(name: str) -> str:
    """Return a setting from .env, or stop with a clear message if it is missing."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is missing. Add it to .env (see .env.example).")
    return value


MODEL = get_setting("GEMINI_MODEL")

# If Google answers "too busy" (429) or has a server error (500, 503),
# wait and try again: 2s, then 4s, 8s, 16s (each wait doubles).
RETRY = types.HttpRetryOptions(
    attempts=5,  # 5 tries in total, counting the first one
    initial_delay=2.0,
    http_status_codes=[429, 500, 503],
)

client = genai.Client(
    api_key=get_setting("GEMINI_API_KEY"),
    http_options=types.HttpOptions(retry_options=RETRY),
)


# We never let the model call Python functions, so switch that feature off.
NO_AFC = types.GenerateContentConfig(
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)


def ask(prompt: str) -> str:
    """Send one prompt to Gemini and return its text reply."""
    response = client.models.generate_content(model=MODEL, contents=prompt, config=NO_AFC)
    return response.text or ""
