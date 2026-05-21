from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def json_dumps_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def json_loads_bytes(data: bytes | str) -> dict[str, Any]:
    raw = data.decode("utf-8") if isinstance(data, bytes) else data
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object.")
    return parsed


def datetime_to_iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    return datetime.fromisoformat(value)
