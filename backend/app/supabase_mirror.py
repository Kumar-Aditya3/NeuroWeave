from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
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


def _read(path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    base_url, service_key, enabled = _config()
    if not enabled or not base_url or not service_key:
        return []

    query = urllib.parse.urlencode(params or {}, doseq=True)
    target = base_url.rstrip("/") + "/rest/v1/" + path.lstrip("/")
    if query:
        target = f"{target}?{query}"

    request = urllib.request.Request(
        target,
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, list):
                return [row for row in payload if isinstance(row, dict)]
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []
    return []


def _normalize_iso(timestamp: str | None) -> str:
    if not timestamp:
        return datetime.now(timezone.utc).isoformat()
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc).isoformat()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def mirror_event(payload: dict[str, Any]) -> bool:
    return _request("POST", "events_raw", payload)


def mirror_device(payload: dict[str, Any]) -> bool:
    return _request("POST", "devices_state", payload, upsert=True, on_conflict="user_id,device_id")


def mirror_feedback(payload: dict[str, Any]) -> bool:
    return _request("POST", "feedback_events", payload)


def mirror_wallpaper_memory(payload: dict[str, Any]) -> bool:
    return _request("POST", "wallpaper_memory", payload)


def mirror_arc_centroids(payloads: list[dict[str, Any]]) -> bool:
    if not payloads:
        return True
    base_url, service_key, enabled = _config()
    if not enabled or not base_url or not service_key:
        return False

    target = base_url.rstrip("/") + "/rest/v1/arc_centroids?" + urllib.parse.urlencode({"on_conflict": "user_id,arc_name"})
    data = json.dumps(payloads).encode("utf-8")
    request = urllib.request.Request(
        target,
        data=data,
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=6):
            return True
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return False


def mirror_user_preferences(payloads: list[dict[str, Any]]) -> bool:
    if not payloads:
        return True
    base_url, service_key, enabled = _config()
    if not enabled or not base_url or not service_key:
        return False

    target = base_url.rstrip("/") + "/rest/v1/user_preferences?" + urllib.parse.urlencode({"on_conflict": "user_id,target_type,target_key"})
    data = json.dumps(payloads).encode("utf-8")
    request = urllib.request.Request(
        target,
        data=data,
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=6):
            return True
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return False


def fetch_recent_events(user_id: str, limit: int = 24) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 100))
    rows = _read(
        "events_raw",
        {
            "select": "id,user_id,device_id,client_name,source,event_type,url,title,category,duration_seconds,sentiment,vibe,created_at,classifier_mode",
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": safe_limit,
        },
    )
    return [
        {
            "id": int(row.get("id", 0)),
            "user_id": str(row.get("user_id", user_id)),
            "device_id": row.get("device_id"),
            "client_name": row.get("client_name"),
            "source": str(row.get("source") or ""),
            "event_type": str(row.get("event_type") or ""),
            "url": row.get("url"),
            "title": row.get("title"),
            "category": row.get("category"),
            "duration_seconds": row.get("duration_seconds"),
            "sentiment": str(row.get("sentiment") or "neutral"),
            "vibe": str(row.get("vibe") or "balanced"),
            "created_at": _normalize_iso(row.get("created_at")),
            "classifier_mode": row.get("classifier_mode"),
        }
        for row in rows
        if row.get("id") is not None
    ]


def fetch_recent_event_payloads(user_id: str, limit: int = 48) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 200))
    rows = _read(
        "events_raw",
        {
            "select": "id,title,url,category,duration_seconds,selected_text,content_text,source,event_type,process_name,topic_scores_json,vibe,created_at",
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": safe_limit,
        },
    )
    payloads: list[dict[str, Any]] = []
    for row in rows:
        payloads.append(
            {
                "id": int(row.get("id", 0)),
                "title": str(row.get("title") or ""),
                "url": str(row.get("url") or ""),
                "category": str(row.get("category") or ""),
                "duration_seconds": int(row.get("duration_seconds") or 0),
                "selected_text": str(row.get("selected_text") or ""),
                "content_text": str(row.get("content_text") or ""),
                "source": str(row.get("source") or ""),
                "event_type": str(row.get("event_type") or ""),
                "process_name": str(row.get("process_name") or ""),
                "topic_scores_json": row.get("topic_scores_json"),
                "vibe": str(row.get("vibe") or "balanced"),
                "created_at": _normalize_iso(row.get("created_at")),
            }
        )
    return payloads


def fetch_wallpaper_memory(user_id: str, limit: int = 36) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 200))
    rows = _read(
        "wallpaper_memory",
        {
            "select": "topic,vibe,style,provider,wallpaper_query,wallpaper_preview_url,created_at",
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": safe_limit,
        },
    )
    return [
        {
            "topic": str(row.get("topic") or "unknown"),
            "vibe": str(row.get("vibe") or "balanced"),
            "style": str(row.get("style") or "minimal"),
            "provider": str(row.get("provider") or "generated_future"),
            "wallpaper_query": str(row.get("wallpaper_query") or ""),
            "wallpaper_preview_url": row.get("wallpaper_preview_url"),
            "created_at": _normalize_iso(row.get("created_at")),
        }
        for row in rows
    ]


def fetch_arc_centroids(user_id: str) -> dict[str, dict[str, Any]]:
    rows = _read(
        "arc_centroids",
        {
            "select": "arc_name,centroid_json,sample_count,dominant_topic,vibe,strength",
            "user_id": f"eq.{user_id}",
        },
    )
    payload: dict[str, dict[str, Any]] = {}
    for row in rows:
        centroid = row.get("centroid_json")
        if not isinstance(centroid, list) or not centroid:
            continue
        payload[str(row.get("arc_name") or "arc")] = {
            "centroid": [float(value) for value in centroid],
            "sample_count": float(row.get("sample_count") or 0.0),
            "dominant_topic": row.get("dominant_topic"),
            "vibe": row.get("vibe"),
            "strength": float(row.get("strength") or 0.0),
        }
    return payload


def fetch_user_preferences(user_id: str) -> dict[str, dict[str, float]]:
    rows = _read(
        "user_preferences",
        {
            "select": "target_type,target_key,score",
            "user_id": f"eq.{user_id}",
        },
    )
    payload: dict[str, dict[str, float]] = {}
    for row in rows:
        bucket = payload.setdefault(str(row.get("target_type") or "general"), {})
        bucket[str(row.get("target_key") or "")] = round(float(row.get("score") or 0.0), 4)
    return payload
