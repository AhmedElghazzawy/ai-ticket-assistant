from dotenv import load_dotenv
from google import genai

load_dotenv()          # loads the key from your .env file
client = genai.Client()  # finds GEMINI_API_KEY automatically

ticket = "Hi, I forgot my student portal password and I can't log in. Can you help?"

response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents=f"You are a university helpdesk assistant. Reply briefly to this student ticket:\n\n{ticket}",
)

print(response.text)
