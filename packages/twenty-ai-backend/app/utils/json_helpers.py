"""JSON serialization helpers for SQLite text fields that store JSON."""

import json


def to_json(value):
    """Serialize a Python value to JSON string for SQLite storage."""
    if value is None:
        return None
    if isinstance(value, str):
        # Already a string — verify it's valid JSON and return as-is
        try:
            json.loads(value)
            return value
        except (json.JSONDecodeError, TypeError):
            return json.dumps(value, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def from_json(value, default=None):
    """Deserialize a JSON string from SQLite to Python object."""
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default
    return default


def embedding_to_db(embedding):
    """Serialize embedding list to JSON string."""
    return to_json(embedding)


def embedding_from_db(value):
    """Deserialize embedding from JSON string to list of floats."""
    parsed = from_json(value)
    if parsed is None:
        return None
    if isinstance(parsed, list):
        return [float(x) for x in parsed]
    return None
