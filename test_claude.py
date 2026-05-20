from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()

client = Anthropic(
    api_key=os.getenv("CLAUDE_API_KEY")
)

message = client.messages.create(
    model="claude-opus-4-1",
    max_tokens=200,
    messages=[
        {
            "role": "user",
            "content": "Bonjour Jarvis"
        }
    ]
)

print(message.content[0].text)