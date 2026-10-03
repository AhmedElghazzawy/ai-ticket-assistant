import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # loads GEMINI_API_KEY (and optional GEMINI_MODEL) from your .env file

# Model name lives in .env so you can switch models without editing code
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

# Retry automatically when Google's servers are busy (429/5xx) instead of crashing
client = genai.Client(
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(attempts=5, initial_delay=2.0)
    )
)

ticket = "Hi, I forgot my student portal password and I can't log in. Can you help?"

response = client.models.generate_content(
    model=MODEL,
    contents=f"You are a university helpdesk assistant. Reply briefly to this student ticket:\n\n{ticket}",
)

print(response.text)
