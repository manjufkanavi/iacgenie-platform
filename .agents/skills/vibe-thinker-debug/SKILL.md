---
name: vibe-thinker-debug
description: Orchestrator-driven debugging skill where ANY capable agent (the orchestrator) does all code reading, tool calling, and editing while VibeThinker-3B acts as the reasoning "brain". The orchestrator holds session state and compressed memory; VibeThinker is a stateless reasoning oracle that proposes hypotheses which the orchestrator validates against reality before applying. Built for long, multi-step debugging sessions.
---

# VibeThinker Debug & Fix

Use VibeThinker-3B (or any small reasoning model) as the **brain** while you (the orchestrator) do all the **eyes and hands** work. This skill is model-agnostic on the orchestrator side — any capable agent can drive it.

## Core Principle

**VibeThinker proposes, you dispose.** It is a reasoning oracle, NOT an agent. It never touches files, never runs commands, never holds state. Every output is a *hypothesis* you validate against reality before acting.

## Division of Labor

| Orchestrator (you) | VibeThinker (brain) |
|---|---|
| Read/search files | Pure reasoning |
| Run tests/commands | Math, logic, algorithm design |
| Tool calling | Bug analysis |
| Context gathering & trimming | Step-by-step derivation |
| Validate & apply results | Answer in `<ANSWER>` block |
| Hold session state | Stateless — one problem per call |

## The Debug Loop

```
1. Gather context (read file, run test, capture error)
2. Build a self-contained problem from CURRENT state
3. Call VibeThinker → get reasoning + <ANSWER>
4. Validate the answer against reality (run it)
5. Apply the edit if valid
6. Re-run test → new error or pass
7. Loop back to step 1 with the NEW state
```

## Session State Object

Maintain this in memory (or a JSON file) across the whole session. **You own the narrative.**

```json
{
  "file": "src/parser.py",
  "original_symptom": "KeyError: 'name' at line 42",
  "current_error": "KeyError: 'name' at line 42",
  "attempts": 3,
  "history": [
    {"tried": "added .get()", "result": "now returns None instead of crashing"},
    {"tried": "checked key presence", "result": "key genuinely missing"}
  ],
  "hypothesis": "dict key missing because caller passes malformed input"
}
```

## The Prompt Template (compressed memory)

Each VibeThinker call is a **fresh, self-contained problem**. Never dump the whole session — compress it.

```
You are a debugging reasoning engine. Given the current state, reason step by
step and return ONLY: (a) your reasoning, (b) a final answer in a
machine-parseable block like <ANSWER>...</ANSWER>.

CURRENT STATE:
- File: <file>
- Original symptom: <original_symptom>
- Current error: <current_error>
- Already tried (do NOT repeat these):
  1. <tried> → <result>
  2. <tried> → <result>
- Relevant code (lines X-Y):
  <trimmed snippet>

QUESTION: Given what's already been tried and failed, what is the most likely
root cause and the next best fix? Return <ANSWER>...</ANSWER>.
```

## How to Call VibeThinker

Use the bundled client `scripts/vibe_client.py` (OpenAI-compatible, streams both channels):

```bash
python3 scripts/vibe_client.py \
  --model "VibeThinker-3B-OptiQ-4bit" \
  --endpoint "http://127.0.0.1:1234/v1" \
  --prompt "$(cat problem.txt)" \
  --max-tokens 2048
```

It prints:
- `reasoning_content` (hidden CoT) to stderr
- `content` (final answer) to stdout
- Extracts the `<ANSWER>...</ANSWER>` block if present

## The Challenges & How to Overcome Them

### 1. Context window / memory loss
3B models can't hold a long session.
**Fix:** Compressed memory — summarize history into 2-3 lines of "tried and failed" before each call. You are the memory; it is a fresh brain each time.

### 2. Repetition / getting stuck in a loop
A 3B will re-suggest what already failed because it doesn't remember.
**Fix:** Explicit "already tried" list in every prompt + a **loop guard** — if it suggests the same thing twice, override and force a different angle.

### 3. Hallucinated fixes
3B models confidently suggest wrong code, especially on unfamiliar APIs.
**Fix:** Never apply blindly. Every suggestion gets validated: run the test, check syntax, verify against actual code. Feed the *new* error back.

### 4. Error drift / losing the thread
After several edits, the original bug may be buried under regressions you introduced.
**Fix:** Keep the original symptom pinned in session state. If 3+ edits without progress, **roll back to a known-good state** (git stash/checkout) and restart fresh.

### 5. Context bloat in the prompt
Long snippets + history = prompt too big for a 3B to reason well.
**Fix:** Aggressive trimming — only the failing function, not the whole file. If the problem genuinely needs lots of context, escalate to a bigger model.

### 6. No conversation memory between calls
VibeThinker is stateless.
**Fix:** You own the narrative — history, hypothesis, attempt counter. Each call is "here's where we are, here's what failed, what next?"

### 7. Cost/latency of many round-trips
Long sessions = many calls, each ~10-15s.
**Fix:** Batch reasoning — group related decisions into one call. Use it only for genuinely hard reasoning steps; do trivial edits yourself.

## The Critical Rule

**VibeThinker proposes, you dispose.** Never let a 3B drive edits without verification. The moment you apply its output unvalidated, you get a compounding mess.

## The One Thing That Makes or Breaks It

**The quality of your compressed memory.** The single biggest failure mode is a 3B re-suggesting what already failed because you didn't tell it clearly. Your "already tried and why it failed" summary is the most important part of every prompt.

## Escalation

For genuinely hard problems where VibeThinker struggles (unfamiliar APIs, huge context, subtle concurrency bugs), escalate to a bigger model (Qwen3.6-35B, gemini) rather than looping forever. VibeThinker is for the "hard thinking" sub-tasks — algorithm design, tricky bug analysis, math, edge cases — not trivial lookups.

## File References
- Client script: `scripts/vibe_client.py`
- Session state helper: `scripts/session_state.py`
