#!/usr/bin/env python3
"""Session state helper for the vibe-thinker-debug skill.

The orchestrator owns the narrative. This helper manages the session state
object (compressed memory) across a long multi-step debugging session.

Usage:
  python3 session_state.py init --file src/parser.py --symptom "KeyError: 'name' at line 42"
  python3 session_state.py add --tried "added .get()" --result "now returns None instead of crashing"
  python3 session_state.py set-error "KeyError: 'name' at line 42"
  python3 session_state.py prompt   # prints the compressed-memory prompt template filled in
  python3 session_state.py show
"""
import argparse
import json
import os
import sys

DEFAULT_STATE = os.path.join(os.path.dirname(__file__), "session_state.json")


def load(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save(state, path):
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def build_prompt(state):
    lines = [
        "You are a debugging reasoning engine. Given the current state, reason step by step",
        "and return ONLY: (a) your reasoning, (b) a final answer in a machine-parseable",
        "block like <ANSWER>...</ANSWER>.",
        "",
        "CURRENT STATE:",
        f"- File: {state.get('file', '?')}",
        f"- Original symptom: {state.get('original_symptom', '?')}",
        f"- Current error: {state.get('current_error', '?')}",
        "- Already tried (do NOT repeat these):",
    ]
    history = state.get("history", [])
    if not history:
        lines.append("  (none yet)")
    for i, h in enumerate(history, 1):
        lines.append(f"  {i}. {h.get('tried')} -> {h.get('result')}")
    if state.get("hypothesis"):
        lines.append(f"- Current hypothesis: {state['hypothesis']}")
    if state.get("snippet"):
        lines.append(f"- Relevant code:\n{state['snippet']}")
    lines += [
        "",
        "QUESTION: Given what's already been tried and failed, what is the most likely",
        "root cause and the next best fix? Return <ANSWER>...</ANSWER>.",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="VibeThinker session state helper")
    ap.add_argument("action", choices=["init", "add", "set-error", "set-snippet", "set-hypothesis", "prompt", "show"])
    ap.add_argument("--file")
    ap.add_argument("--symptom")
    ap.add_argument("--tried")
    ap.add_argument("--result")
    ap.add_argument("--error")
    ap.add_argument("--snippet")
    ap.add_argument("--hypothesis")
    ap.add_argument("--state", default=DEFAULT_STATE)
    args = ap.parse_args()

    state = load(args.state)

    if args.action == "init":
        state = {
            "file": args.file,
            "original_symptom": args.symptom,
            "current_error": args.symptom,
            "attempts": 0,
            "history": [],
            "hypothesis": None,
            "snippet": None,
        }
        save(state, args.state)
        print(f"Initialized session state at {args.state}")

    elif args.action == "add":
        state.setdefault("history", [])
        state["history"].append({"tried": args.tried, "result": args.result})
        state["attempts"] = state.get("attempts", 0) + 1
        save(state, args.state)
        print(f"Added attempt {state['attempts']}")

    elif args.action == "set-error":
        state["current_error"] = args.error
        save(state, args.state)
        print("Updated current error")

    elif args.action == "set-snippet":
        state["snippet"] = args.snippet
        save(state, args.state)
        print("Updated code snippet")

    elif args.action == "set-hypothesis":
        state["hypothesis"] = args.hypothesis
        save(state, args.state)
        print("Updated hypothesis")

    elif args.action == "prompt":
        print(build_prompt(state))

    elif args.action == "show":
        print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
