"""Shared Gemini setup, so every script connects the same way."""

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # loads GEMINI_API_KEY (and optional GEMINI_MODEL) from your .env file

# Model name lives in .env so you can switch models without editing code
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Retry automatically when Google's servers are busy (429/5xx) instead of crashing
client = genai.Client(
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(attempts=6, initial_delay=5.0)
    )
)
