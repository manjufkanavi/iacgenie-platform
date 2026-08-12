#!/usr/bin/env python3
"""Convert raw SAST tool output into a normalized JSON artifact.

Usage: sast-parse <tool> <input-file> <output-file>
"""
import json
import re
import sys


def parse_ruff(path):
    d = json.load(open(path))
    return {
        "tool": "ruff",
        "total": len(d),
        "errors": [
            {
                "file": x["filename"],
                "code": x["code"],
                "line": x["location"]["row"],
                "column": x["location"]["column"],
                "message": x["message"],
            }
            for x in d
        ],
    }


def parse_bandit(path):
    d = json.load(open(path))
    res = d.get("results", [])
    return {
        "tool": "bandit",
        "total": len(res),
        "errors": [
            {
                "file": r["filename"],
                "test_id": r["test_id"],
                "severity": r["issue_severity"],
                "confidence": r["issue_confidence"],
                "text": r["issue_text"],
            }
            for r in res
        ],
    }


def parse_semgrep(path):
    d = json.load(open(path))
    res = d.get("results", [])
    return {
        "tool": "semgrep",
        "total": len(res),
        "errors": [
            {
                "file": r["path"],
                "check_id": r["check_id"],
                "severity": r["extra"].get("severity"),
                "message": r["extra"].get("message"),
            }
            for r in res
        ],
    }


def parse_mypy(path):
    lines = [l for l in open(path) if ": error:" in l]
    errors = []
    for l in lines:
        m = re.match(r"^([^:]+):(\d+): error: (.*)$", l.strip())
        if m:
            errors.append({"file": m.group(1), "line": int(m.group(2)), "message": m.group(3)})
    return {"tool": "mypy", "total": len(errors), "errors": errors}


def parse_eslint(path):
    d = json.load(open(path))
    msgs = [m for x in d for m in x["messages"]]
    return {
        "tool": "eslint",
        "files": len(d),
        "total": len(msgs),
        "errors": [
            {
                "file": x["filePath"],
                "line": m["line"],
                "column": m["column"],
                "rule": m["ruleId"],
                "severity": m["severity"],
                "message": m["message"],
            }
            for x in d
            for m in x["messages"]
        ],
    }


def parse_gitleaks(path):
    d = json.load(open(path))
    return {
        "tool": "gitleaks",
        "total": len(d),
        "errors": [
            {
                "file": f["File"],
                "rule": f["RuleID"],
                "secret": f["Secret"],
                "start_line": f["StartLine"],
                "end_line": f["EndLine"],
            }
            for f in d
        ],
    }


PARSERS = {
    "ruff": parse_ruff,
    "bandit": parse_bandit,
    "semgrep": parse_semgrep,
    "mypy": parse_mypy,
    "eslint": parse_eslint,
    "gitleaks": parse_gitleaks,
}


def main():
    if len(sys.argv) != 4:
        print("usage: sast-parse <tool> <input> <output>", file=sys.stderr)
        sys.exit(2)
    tool, inp, out = sys.argv[1], sys.argv[2], sys.argv[3]
    try:
        result = PARSERS[tool](inp)
    except FileNotFoundError:
        result = {"tool": tool, "total": 0, "errors": [], "note": "no output produced"}
    except Exception as e:  # noqa: BLE001
        result = {"tool": tool, "total": 0, "errors": [], "note": f"parse error: {e}"}
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"{tool}: {result['total']} findings")


if __name__ == "__main__":
    main()
