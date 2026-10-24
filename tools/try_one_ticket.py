"""Step 1 check: send one ticket to Gemini and print the reply."""

from helpdesk.ai.gemini import ask
from helpdesk.core.settings import get_settings

TICKET = "I forgot my password and the reset email never arrives. I have an exam tomorrow."

prompt = f"You are a university helpdesk assistant. Reply briefly to this ticket:\n\n{TICKET}"

print(f"Model: {get_settings().gemini_model}\n")
print(ask(prompt))
