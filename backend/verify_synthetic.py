from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    temp_root = Path(tempfile.mkdtemp(prefix="neuroweave_synth_"))
    db_path = temp_root / "synthetic.db"
    os.environ["NEUROWEAVE_DB_PATH"] = str(db_path)
    os.environ["NEUROWEAVE_API_KEYS"] = "synthetic-key"

    from app.main import app

    headers = {"X-API-Key": "synthetic-key"}
    user_id = "synthetic-user"

    with TestClient(app) as client:
        health = client.get("/health")
        _assert(health.status_code == 200, "Health endpoint failed")

        page_payload = {
            "user_id": user_id,
            "device_id": "laptop-01",
            "client_name": "Laptop",
            "url": "https://example.com/course/deep-learning",
            "title": "Deep learning exam prep notes",
            "selected_text": "focused study schedule and assignments",
            "timestamp": _iso_now(),
        }
        page_ingest = client.post("/ingest/page", json=page_payload, headers=headers)
        _assert(page_ingest.status_code == 200, f"Page ingest failed: {page_ingest.text}")

        pdf_payload = {
            "user_id": user_id,
            "device_id": "desktop-01",
            "client_name": "Desktop",
            "filename": "systems-design.pdf",
            "text": "architecture, distributed systems, software trade-offs",
            "timestamp": _iso_now(),
        }
        pdf_ingest = client.post("/ingest/pdf", json=pdf_payload, headers=headers)
        _assert(pdf_ingest.status_code == 200, f"PDF ingest failed: {pdf_ingest.text}")

        activity_events = [
            {
                "user_id": user_id,
                "device_id": "laptop-01",
                "client_name": "Laptop",
                "source": "active_window",
                "event_type": "active_window",
                "title": "VS Code - backend refactor",
                "process_name": "code.exe",
                "category": "coding",
                "duration_seconds": 420,
                "content_text": "python fastapi model update",
                "timestamp": _iso_now(),
            },
            {
                "user_id": user_id,
                "device_id": "desktop-01",
                "client_name": "Desktop",
                "source": "game",
                "event_type": "game",
                "title": "Valorant ranked session",
                "process_name": "valorant-win64-shipping.exe",
                "category": "gaming",
                "duration_seconds": 1800,
                "content_text": "competitive match intense focus",
                "timestamp": _iso_now(),
            },
            {
                "user_id": user_id,
                "device_id": "laptop-01",
                "client_name": "Laptop",
                "source": "mobile_share",
                "event_type": "mobile_share",
                "title": "Shared article from phone",
                "url": "https://example.com/ai-news",
                "category": "mobile_share",
                "duration_seconds": 35,
                "content_text": "breaking ai news and research highlights",
                "timestamp": _iso_now(),
            },
        ]

        for payload in activity_events:
            response = client.post("/ingest/activity", json=payload, headers=headers)
            _assert(response.status_code == 200, f"Activity ingest failed: {response.text}")

        dedupe_timestamp = _iso_now()
        dedupe_payload = {
            "user_id": user_id,
            "device_id": "laptop-01",
            "client_name": "Laptop",
            "source": "active_window",
            "event_type": "active_window",
            "title": "VS Code - backend refactor",
            "process_name": "code.exe",
            "category": "coding",
            "duration_seconds": 40,
            "timestamp": dedupe_timestamp,
        }
        first = client.post("/ingest/activity", json=dedupe_payload, headers=headers)
        second = client.post("/ingest/activity", json=dedupe_payload, headers=headers)
        _assert(first.status_code == 200 and second.status_code == 200, "Dedupe ingest requests failed")
        _assert(second.json().get("deduped") is True, "Expected second ingest to be deduped")

        recommendation_queries = []
        for _ in range(3):
            recommendation = client.get(
                "/recommend/context",
                params={
                    "user_id": user_id,
                    "classifier_mode": "embedding_primary",
                    "recommendation_intensity": "balanced",
                    "wallpaper_style": "minimal",
                    "wallpaper_provider": "curated_unsplash",
                },
                headers=headers,
            )
            _assert(recommendation.status_code == 200, f"Recommendation failed: {recommendation.text}")
            recommendation_queries.append(recommendation.json().get("wallpaper_query", ""))

        _assert(len(set(recommendation_queries)) >= 2, "Wallpaper memory did not diversify repeated queries")

        sources = client.get("/me/sources", params={"user_id": user_id}, headers=headers)
        _assert(sources.status_code == 200, f"Sources endpoint failed: {sources.text}")
        source_payload = sources.json()["sources"]
        source_names = {row["client_name"] for row in source_payload}
        _assert({"Laptop", "Desktop"}.issubset(source_names), "Expected both laptop and desktop in sources")

        recent_events = client.get(
            "/me/recent-events",
            params={"user_id": user_id, "limit": 25},
            headers=headers,
        )
        _assert(recent_events.status_code == 200, f"Recent events failed: {recent_events.text}")
        _assert(len(recent_events.json().get("events", [])) >= 5, "Expected multiple synthetic events")
        _assert(
            any((event.get("duration_seconds") or 0) > 0 for event in recent_events.json().get("events", [])),
            "Expected duration-aware events",
        )

        dashboard = client.get(
            "/me/dashboard",
            params={
                "user_id": user_id,
                "limit": 24,
                "classifier_mode": "embedding_primary",
                "recommendation_intensity": "balanced",
                "wallpaper_style": "minimal",
                "wallpaper_provider": "curated_unsplash",
            },
            headers=headers,
        )
        _assert(dashboard.status_code == 200, f"Dashboard failed: {dashboard.text}")
        dashboard_payload = dashboard.json()
        _assert(len(dashboard_payload.get("current_arcs", [])) > 0, "Expected adaptive arcs in dashboard")
        mix = dashboard_payload.get("source_mix", {})
        _assert(mix.get("mobile", 0) >= 1, "Expected mobile contribution in source mix")
        _assert(dashboard_payload.get("recommendation", {}).get("wallpaper_rationale"), "Missing wallpaper rationale")

        topic = dashboard_payload["recommendation"].get("primary_topic", "unknown")
        feedback = client.post(
            "/feedback",
            json={
                "user_id": user_id,
                "recommendation_topic": topic,
                "action": "keep",
            },
            headers=headers,
        )
        _assert(feedback.status_code == 200, f"Feedback endpoint failed: {feedback.text}")

    print("Synthetic validation passed")
    print(f"Database: {db_path}")


if __name__ == "__main__":
    main()
