#!/usr/bin/env python3
"""
Remote model caller for non-tool-calling models (Antares, VibeThinker).

These models respond via OpenAI-compatible API at 127.0.0.1:1234 but do NOT
support tool/function calling. All context must be passed as text in the prompt.

Usage:
    python3 remote_model_caller.py <model> "<system prompt>" "<user prompt>"
    python3 remote_model_caller.py antares "You are a devops engineer..." "Audit the service..."
    python3 remote_model_caller.py vibethinker "You are a secops engineer..." "Audit the service..."

Output: JSON to stdout (the model's response, stripped of markdown code fences).
"""

import json
import sys
import urllib.request
import urllib.error


API_URL = "http://127.0.0.1:1234/v1/chat/completions"
TIMEOUT = 300  # seconds — these are small models, should be fast


def call_model(model_name: str, system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> str:
    """Call a remote model and return the response text."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    payload = json.dumps({
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer not-needed",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"].strip()
            return content
    except urllib.error.URLError as e:
        return json.dumps({"error": f"API call failed: {e}", "model": model_name})


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: remote_model_caller.py <model> <system_prompt> [user_prompt]"}), file=sys.stderr)
        sys.exit(1)

    model_name = sys.argv[1]

    # Args 2..N are the prompt parts (joined with spaces)
    # First arg after model is system prompt, rest is user prompt
    if len(sys.argv) == 3:
        # Only one prompt arg — use as system prompt, empty user prompt
        system_prompt = sys.argv[2]
        user_prompt = ""
    else:
        # First prompt arg = system, rest = user
        system_prompt = sys.argv[2]
        user_prompt = " ".join(sys.argv[3:])

    response = call_model(model_name, system_prompt, user_prompt)
    print(response)


if __name__ == "__main__":
    main()
