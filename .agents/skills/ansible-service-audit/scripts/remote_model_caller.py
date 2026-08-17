#!/usr/bin/env python3
"""
Remote model caller for non-tool-calling models (Antares, VibeThinker).

These models respond via OpenAI-compatible API at 127.0.0.1:1234 but do NOT
support tool/function calling. All context must be passed as text in the prompt.

Usage:
    python3 remote_model_caller.py <model> "<system prompt>" "<user prompt>"
    python3 remote_model_caller.py antares-1b-mlx-8bit "You are a devops engineer..." "Audit the service..."
    python3 remote_model_caller.py VibeThinker-3B-OptiQ-4bit "You are a secops engineer..." "Audit the service..."

Environment variables:
    MODEL_API_URL    - API endpoint (default: http://127.0.0.1:1234/v1/chat/completions)
    MODEL_TIMEOUT    - Per-request timeout in seconds (default: 300)
    MODEL_RETRIES    - Max retry attempts on failure (default: 2)
    MODEL_TEMPERATURE - Temperature for generation (default: 0.1)

Output: JSON to stdout (the model's response, stripped of markdown code fences).
        On failure: {"error": "...", "model": "...", "attempt": N}

Parallel usage:
    Use concurrent.futures.ThreadPoolExecutor to run multiple callers in parallel.
    Example:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(call_model, m, sys, usr) for m, sys, usr in tasks]
            results = [f.result() for f in futures]
"""

import json
import sys
import time
import urllib.request
import urllib.error
import os


DEFAULT_API_URL = "http://127.0.0.1:1234/v1/chat/completions"
DEFAULT_TIMEOUT = int(os.environ.get("MODEL_TIMEOUT", "300"))
DEFAULT_RETRIES = int(os.environ.get("MODEL_RETRIES", "2"))
DEFAULT_TEMPERATURE = float(os.environ.get("MODEL_TEMPERATURE", "0.1"))


def call_model(model_name: str, system_prompt: str, user_prompt: str,
               api_url: str = None, timeout: int = None,
               retries: int = None, temperature: float = None) -> dict:
    """
    Call a remote model and return the response as a dict.
    On success: {"model": name, "content": "...", "success": True}
    On failure: {"model": name, "content": "", "success": False, "error": "...", "attempt": N}
    """
    api_url = api_url or os.environ.get("MODEL_API_URL", DEFAULT_API_URL)
    timeout = timeout or DEFAULT_TIMEOUT
    retries = retries if retries is not None else DEFAULT_RETRIES
    temperature = temperature if temperature is not None else DEFAULT_TEMPERATURE

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(1, retries + 2):  # 1 initial + retries
        payload = json.dumps({
            "model": model_name,
            "messages": messages,
            "max_tokens": 8192,
            "temperature": temperature,
        }).encode("utf-8")

        req = urllib.request.Request(
            api_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer not-needed",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read())
                content = result["choices"][0]["message"]["content"].strip()
                return {
                    "model": model_name,
                    "content": content,
                    "success": True,
                    "attempt": attempt,
                    "timestamp": time.time(),
                }
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError) as e:
            if attempt <= retries:
                # Backoff before retry
                time.sleep(min(2 ** attempt, 10))
                continue
            return {
                "model": model_name,
                "content": "",
                "success": False,
                "error": f"API call failed after {attempt} attempts: {type(e).__name__}: {e}",
                "attempt": attempt,
                "timestamp": time.time(),
            }


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            "error": "Usage: remote_model_caller.py <model> <system_prompt> [user_prompt]",
            "success": False
        }), file=sys.stderr)
        sys.exit(1)

    model_name = sys.argv[1]

    # Args 2..N are the prompt parts (joined with spaces)
    if len(sys.argv) == 3:
        system_prompt = sys.argv[2]
        user_prompt = ""
    else:
        system_prompt = sys.argv[2]
        user_prompt = " ".join(sys.argv[3:])

    result = call_model(model_name, system_prompt, user_prompt)

    # Strip markdown code fences if present
    content = result["content"]
    if content.startswith("```") and content.endswith("```"):
        lines = content.split("\n")
        lines = lines[1:-1]  # Remove first and last ``` line
        content = "\n".join(lines)

    result["content"] = content
    print(json.dumps(result))


if __name__ == "__main__":
    main()
