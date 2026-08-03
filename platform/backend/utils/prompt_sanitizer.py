import re

MAX_PROMPT_LENGTH = 10000
BLOCKED_PATTERNS = [
    r"(?i)system.*override",
    r"(?i)ignore.*previous.*instructions",
    r"(?i)as.*k.*telling",
    r"(?i)\{\{.*USER_PROMPT.*\}\}",  # template injection
]


def sanitize_prompt(prompt: str) -> str:
    # Validate length
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ValueError(
            f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters"
        )
    # Check for blocked patterns (prompt injection)
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, prompt):
            raise ValueError("Prompt contains potentially malicious content")
    # Strip control characters
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", prompt)
    return sanitized.strip()
