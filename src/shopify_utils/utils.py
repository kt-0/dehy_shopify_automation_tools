"""
utils.py — General helpers for Shopify scripts.
"""

import inspect
import json
import re


def sanitize(value: str) -> str:
    """Convert a string into a safe handle format for Shopify (lowercase, underscores)."""
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r'[^a-z0-9_]+', '_', value.strip().lower())


def title_case(value: str) -> str:
    """Return a human-readable title string."""
    return value.replace("_", " ").strip().title()


def log(message: str) -> None:
    """Print message with the calling line number for easier debugging."""
    frame = inspect.currentframe().f_back
    print(f"[Line {frame.f_lineno}] {message}")


def recursive_dict_search(data, key, target_value=None):
    """
    Recursively search through nested dicts/lists for a key (and optional value).
    """
    if isinstance(data, dict):
        if key in data and (target_value is None or data[key] == target_value):
            return data[key]
        for v in data.values():
            found = recursive_dict_search(v, key, target_value)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = recursive_dict_search(item, key, target_value)
            if found is not None:
                return found
    return None


def pretty_json(obj) -> str:
    """Return a formatted JSON string for debugging."""
    return json.dumps(obj, indent=2, ensure_ascii=False)
