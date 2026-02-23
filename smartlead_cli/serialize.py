"""Serialization helpers for JSON and HTTP responses."""

from __future__ import annotations

import base64
from datetime import date, datetime
from pathlib import Path
from typing import Any


def to_data(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return {
                "type": "bytes",
                "encoding": "base64",
                "size": len(obj),
                "data": base64.b64encode(obj).decode("ascii"),
            }
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): to_data(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_data(v) for v in obj]
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return to_data(obj.model_dump(by_alias=True, exclude_none=True))
        except TypeError:
            return to_data(obj.model_dump())
    if hasattr(obj, "__dict__"):
        return to_data(vars(obj))
    return str(obj)
