import json
import re
from typing import Any, Dict

JSON_CANDIDATE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(payload: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Attempt to coerce the LLM payload into JSON."""
    payload = payload.strip()
    if not payload:
        return fallback

    try:
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    match = JSON_CANDIDATE.search(payload)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return fallback
    return fallback

