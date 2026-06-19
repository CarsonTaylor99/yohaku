"""Small helpers shared across the backend. Defensive JSON parsing lives here
because every structured stage needs it (CLAUDE.md "parse defensively")."""
from __future__ import annotations

import json


class ModelJSONError(ValueError):
    """Raised when an LLM response can't be parsed as JSON."""


def parse_json(text: str):
    """Parse JSON from a model response, tolerating fences and surrounding chatter."""
    s = text.strip()

    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    if s.startswith("```"):
        nl = s.find("\n")
        if nl != -1:
            s = s[nl + 1 :]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass

    for opener, closer in [("{", "}"), ("[", "]")]:
        block = _extract_balanced(s, opener, closer)
        if block is not None:
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                continue

    preview = text[:200].replace("\n", " ")
    raise ModelJSONError(f"Could not parse JSON from model output: {preview!r}")


def _extract_balanced(s: str, opener: str, closer: str) -> str | None:
    """First balanced opener..closer block, respecting JSON string escapes."""
    start = s.find(opener)
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(s)):
        c = s[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None
