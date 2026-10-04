from llm import MODEL, client  # shared Gemini setup (API key, model, retries)

ticket = "Hi, I forgot my student portal password and I can't log in. Can you help?"

response = client.models.generate_content(
    model=MODEL,
    contents=f"You are a university helpdesk assistant. Reply briefly to this student ticket:\n\n{ticket}",
)

print(response.text)
