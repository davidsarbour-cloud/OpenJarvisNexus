"""
Manual probe — find the first Claude model your API key can reach.

Invoked as `python backend/tests/test_claude.py`. Imports that need
third-party deps (anthropic, dotenv) live inside main() so pytest's
collection-time import doesn't pull them in.
"""
import os


def main() -> None:
    from anthropic import Anthropic, APIError
    from dotenv import load_dotenv

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
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-6",
        "claude-opus-4-7",
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


if __name__ == "__main__":
    main()
