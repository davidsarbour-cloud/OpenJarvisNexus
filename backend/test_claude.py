"""Clean test — no syntax errors."""
import os
from dotenv import load_dotenv
from anthropic import Anthropic, APIError

load_dotenv(override=True)
key = os.getenv("ANTHROPIC_API_KEY", "")

print(f"OS-level key : {os.environ.get('ANTHROPIC_API_KEY', '(none)')[:25]}...")
print(f".env key     : {key[:25]}...")
print(f"Key length   : {len(key)}")
print(f"Has spaces   : {' ' in key}")
print()

if not key:
    raise SystemExit("No key found in .env")

client = Anthropic(api_key=key)

models = [
    "claude-3-5-sonnet-20241022",
    "claude-3-haiku-20240307",
    "claude-3-sonnet-20240229",
    "claude-3-opus-20240229",
]

for model in models:
    print(f"Testing: {model}")
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=30,
            messages=[{"role": "user", "content": "say pong"}],
        )
        text = resp.content[0].text
        print(f"  SUCCESS: {text!r}")
        print(f"  USE THIS: CLAUDE_MODEL={model}")
        break
    except APIError as e:
        code = getattr(e, "status_code", "?")
        print(f"  FAILED {code}: {e}")
    print()