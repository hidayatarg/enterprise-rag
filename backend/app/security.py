
import re

# This is a list of regex patterns that are considered suspicious and may indicate prompt injection attempts.
# This can catch simple, known attack phrases.
SUSPICIOUS_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"system\s+override\s*:",
    r"disregard\s+(all\s+)?prior\s+instructions",
    r"print\s+(all\s+)?secret\s+api\s+keys",
]


def contains_prompt_injection(text: str) -> bool:
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return True

    return False
