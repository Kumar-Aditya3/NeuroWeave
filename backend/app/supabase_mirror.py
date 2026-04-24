from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _config() -> tuple[str | None, str | None, bool]:
    url = os.getenv("NEUROWEAVE_SUPABASE_URL")
    service_key = os.getenv("NEUROWEAVE_SUPABASE_SERVICE_ROLE_KEY")
    enabled = _bool_env("NEUROWEAVE_SUPABASE_ENABLED", False)
    return url, service_key, enabled


def _request(method: str, path: str, payload: dict[str, Any], upsert: bool = False, on_conflict: str | None = None) -> bool:
    base_url, service_key, enabled = _config()
    if not enabled or not base_url or not service_key:
        return False

    target = base_url.rstrip("/") + "/rest/v1/" + path.lstrip("/")
    if upsert and on_conflict:
        target = f"{target}?{urllib.parse.urlencode({'on_conflict': on_conflict})}"

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    if upsert:
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"

    request = urllib.request.Request(target, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=4):
            return True
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return False


def mirror_event(payload: dict[str, Any]) -> bool:
    return _request("POST", "events_raw", payload)


def mirror_device(payload: dict[str, Any]) -> bool:
    return _request("POST", "devices_state", payload, upsert=True, on_conflict="user_id,device_id")


def mirror_feedback(payload: dict[str, Any]) -> bool:
    return _request("POST", "feedback_events", payload)
