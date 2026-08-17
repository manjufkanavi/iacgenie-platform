#!/usr/bin/env python3
"""VibeThinker client for the vibe-thinker-debug skill.

Streams both channels from an OpenAI-compatible endpoint:
  - reasoning_content (hidden CoT) -> stderr
  - content (final answer)         -> stdout
  - extracts <ANSWER>...</ANSWER> block if present

Usage:
  python3 vibe_client.py --model "VibeThinker-3B-OptiQ-4bit" \
      --endpoint "http://127.0.0.1:1234/v1" \
      --prompt "$(cat problem.txt)" \
      --max-tokens 2048
"""
import argparse
import json
import sys
import urllib.request


def stream_chat(endpoint, model, prompt, max_tokens, temperature, top_p):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "stream": True,
    }
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    reasoning = []
    content = []
    with urllib.request.urlopen(req, timeout=600) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except Exception:
                continue
            delta = obj.get("choices", [{}])[0].get("delta", {})
            if delta.get("reasoning_content"):
                reasoning.append(delta["reasoning_content"])
            if delta.get("content"):
                content.append(delta["content"])
    return "".join(reasoning), "".join(content)


def extract_answer(content):
    """Return the <ANSWER>...</ANSWER> block if present, else None."""
    start = content.find("<ANSWER>")
    end = content.find("</ANSWER>")
    if start != -1 and end != -1 and end > start:
        return content[start + len("<ANSWER>"):end].strip()
    return None


def main():
    ap = argparse.ArgumentParser(description="VibeThinker streaming client")
    ap.add_argument("--model", required=True)
    ap.add_argument("--endpoint", default="http://127.0.0.1:1234/v1")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--top-p", type=float, default=0.95)
    args = ap.parse_args()

    reasoning, content = stream_chat(
        args.endpoint, args.model, args.prompt,
        args.max_tokens, args.temperature, args.top_p,
    )

    if reasoning:
        print("=== REASONING (stderr) ===", file=sys.stderr)
        print(reasoning, file=sys.stderr)

    print("=== CONTENT ===")
    print(content)

    answer = extract_answer(content)
    if answer:
        print("\n=== ANSWER BLOCK ===")
        print(answer)


if __name__ == "__main__":
    main()
