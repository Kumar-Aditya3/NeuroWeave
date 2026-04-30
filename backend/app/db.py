import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("NEUROWEAVE_DB_PATH", str(ROOT / "data.db")))
SCHEMA_PATH = ROOT / "sql" / "schema.sql"

TOPICS = [
    "tech",
    "education",
    "anime",
    "fitness",
    "philosophy",
    "self-help",
    "news",
    "unknown",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        _run_migrations(conn)
        conn.commit()


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _run_migrations(conn: sqlite3.Connection) -> None:
    if not _column_exists(conn, "events", "device_id"):
        conn.execute("ALTER TABLE events ADD COLUMN device_id TEXT")
    if not _column_exists(conn, "events", "client_name"):
        conn.execute("ALTER TABLE events ADD COLUMN client_name TEXT")
    if not _column_exists(conn, "events", "category"):
        conn.execute("ALTER TABLE events ADD COLUMN category TEXT")
    if not _column_exists(conn, "events", "duration_seconds"):
        conn.execute("ALTER TABLE events ADD COLUMN duration_seconds INTEGER")
    if not _column_exists(conn, "events", "dedupe_key"):
        conn.execute("ALTER TABLE events ADD COLUMN dedupe_key TEXT")
    if not _column_exists(conn, "events", "embedding_json"):
        conn.execute("ALTER TABLE events ADD COLUMN embedding_json TEXT")
    if not _column_exists(conn, "events", "classifier_mode"):
        conn.execute("ALTER TABLE events ADD COLUMN classifier_mode TEXT")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_events_dedupe_key
        ON events(dedupe_key)
        WHERE dedupe_key IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS arc_centroids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            arc_name TEXT NOT NULL,
            centroid_json TEXT NOT NULL,
            sample_count REAL NOT NULL,
            dominant_topic TEXT,
            vibe TEXT,
            strength REAL,
            updated_at TEXT NOT NULL,
            UNIQUE (user_id, arc_name)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS wallpaper_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            vibe TEXT NOT NULL,
            style TEXT NOT NULL,
            provider TEXT NOT NULL,
            wallpaper_query TEXT NOT NULL,
            wallpaper_preview_url TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wallpaper_memory_user_created
        ON wallpaper_memory(user_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_key TEXT NOT NULL,
            score REAL NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (user_id, target_type, target_key)
        )
        """
    )


def create_event(
    *,
    user_id: str,
    device_id: str | None,
    client_name: str | None,
    source: str,
    event_type: str,
    url: str | None,
    title: str | None,
    category: str | None,
    duration_seconds: int | None,
    selected_text: str | None,
    content_text: str | None,
    topic_scores: Dict[str, float],
    embedding_json: str | None,
    classifier_mode: str | None,
    sentiment: str,
    vibe: str,
    created_at: str,
    dedupe_key: str | None = None,
) -> Tuple[int, bool]:
    payload = {
        "user_id": user_id,
        "device_id": device_id,
        "client_name": client_name,
        "source": source,
        "event_type": event_type,
        "url": url,
        "title": title,
        "category": category,
        "duration_seconds": duration_seconds,
        "selected_text": selected_text,
        "content_text": content_text,
        "topic_scores_json": json.dumps(topic_scores),
        "embedding_json": embedding_json,
        "classifier_mode": classifier_mode,
        "sentiment": sentiment,
        "vibe": vibe,
        "created_at": created_at,
        "dedupe_key": dedupe_key,
    }
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO events (
                user_id, device_id, client_name, source, event_type, url, title, selected_text,
                category, duration_seconds, content_text, topic_scores_json, embedding_json, classifier_mode, sentiment, vibe, created_at, dedupe_key
            )
            VALUES (
                :user_id, :device_id, :client_name, :source, :event_type, :url, :title, :selected_text,
                :category, :duration_seconds, :content_text, :topic_scores_json, :embedding_json, :classifier_mode, :sentiment, :vibe, :created_at, :dedupe_key
            )
            """,
            payload,
        )
        if cursor.rowcount == 0 and dedupe_key:
            row = conn.execute(
                "SELECT id FROM events WHERE dedupe_key = ?",
                (dedupe_key,),
            ).fetchone()
            conn.commit()
            return int(row["id"]), True
        conn.commit()
        return int(cursor.lastrowid), False


def upsert_profile_score(
    user_id: str,
    window: str,
    topic: str,
    incoming_score: float,
    decay: float,
) -> None:
    now = utc_now_iso()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT score
            FROM profile_scores
            WHERE user_id = ? AND window = ? AND topic = ?
            """,
            (user_id, window, topic),
        ).fetchone()
        if row is None:
            new_score = incoming_score
            conn.execute(
                """
                INSERT INTO profile_scores (user_id, window, topic, score, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, window, topic, new_score, now),
            )
        else:
            new_score = (float(row["score"]) * decay) + incoming_score
            conn.execute(
                """
                UPDATE profile_scores
                SET score = ?, updated_at = ?
                WHERE user_id = ? AND window = ? AND topic = ?
                """,
                (new_score, now, user_id, window, topic),
            )
        conn.commit()


def update_profiles(user_id: str, topic_scores: Dict[str, float]) -> None:
    for topic in TOPICS:
        incoming = float(topic_scores.get(topic, 0.0))
        if incoming <= 0:
            continue
        upsert_profile_score(
            user_id=user_id,
            window="short_term",
            topic=topic,
            incoming_score=incoming,
            decay=0.85,
        )
        upsert_profile_score(
            user_id=user_id,
            window="long_term",
            topic=topic,
            incoming_score=incoming,
            decay=0.97,
        )


def get_weighted_profile(user_id: str) -> Dict[str, float]:
    weighted: Dict[str, float] = {topic: 0.0 for topic in TOPICS}
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT window, topic, score
            FROM profile_scores
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()
    for row in rows:
        topic = row["topic"]
        if topic not in weighted:
            continue
        score = float(row["score"])
        if row["window"] == "short_term":
            weighted[topic] += score * 0.7
        else:
            weighted[topic] += score * 0.3
    return weighted


def get_latest_vibe(user_id: str) -> str:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT vibe
            FROM events
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    return str(row["vibe"]) if row else "balanced"


def create_feedback(
    user_id: str,
    recommendation_topic: str,
    action: str,
    recommendation_vibe: str | None = None,
    wallpaper_style: str | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO feedback (user_id, recommendation_topic, action, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, recommendation_topic, action, utc_now_iso()),
        )
        conn.commit()
    update_user_preference(user_id, "topic", recommendation_topic, action)
    if recommendation_vibe:
        update_user_preference(user_id, "vibe", recommendation_vibe, action)
    if wallpaper_style:
        update_user_preference(user_id, "style", wallpaper_style, action)


def upsert_device(user_id: str, device_id: str, client_name: str) -> None:
    now = utc_now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO devices (user_id, device_id, client_name, last_seen_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, device_id)
            DO UPDATE SET
                client_name = excluded.client_name,
                last_seen_at = excluded.last_seen_at
            """,
            (user_id, device_id, client_name, now),
        )
        conn.commit()


def get_user_sources(user_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT device_id, client_name, last_seen_at
            FROM devices
            WHERE user_id = ?
            ORDER BY last_seen_at DESC
            """,
            (user_id,),
        ).fetchall()

    filtered: list[dict] = []
    for row in rows:
        device_id = str(row["device_id"] or "")
        client_name = str(row["client_name"] or "")
        combined = f"{device_id} {client_name}".lower()
        if (
            "synthetic" in combined
            or "-test" in combined
            or "cli test" in combined
            or "live test" in combined
            or "test device" in combined
            or combined.startswith("test ")
        ):
            continue

        filtered.append(
            {
                "device_id": device_id,
                "client_name": client_name,
                "last_seen_at": str(row["last_seen_at"]),
            }
        )
        if len(filtered) >= 2:
            break

    return filtered


def get_recent_events(user_id: str, limit: int = 20) -> list[dict]:
    safe_limit = max(1, min(limit, 100))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, device_id, client_name, source, event_type,
                   url, title, category, duration_seconds, sentiment, vibe, created_at, classifier_mode
            FROM events
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, safe_limit),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "user_id": str(row["user_id"]),
            "device_id": row["device_id"],
            "client_name": row["client_name"],
            "source": str(row["source"]),
            "event_type": str(row["event_type"]),
            "url": row["url"],
            "title": row["title"],
            "category": row["category"],
            "duration_seconds": row["duration_seconds"],
            "sentiment": str(row["sentiment"]),
            "vibe": str(row["vibe"]),
            "created_at": str(row["created_at"]),
            "classifier_mode": row["classifier_mode"],
        }
        for row in rows
    ]


def get_recent_event_payloads(user_id: str, limit: int = 60) -> list[dict]:
    safe_limit = max(1, min(limit, 200))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, url, category, duration_seconds, selected_text, content_text, source, event_type, created_at
            FROM events
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, safe_limit),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "title": row["title"] or "",
            "url": row["url"] or "",
            "category": row["category"] or "",
            "duration_seconds": row["duration_seconds"] or 0,
            "selected_text": row["selected_text"] or "",
            "content_text": row["content_text"] or "",
            "source": row["source"] or "",
            "event_type": row["event_type"] or "",
            "created_at": row["created_at"] or utc_now_iso(),
        }
        for row in rows
    ]


def get_arc_centroids(user_id: str) -> dict[str, dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT arc_name, centroid_json, sample_count, dominant_topic, vibe, strength
            FROM arc_centroids
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()

    payload: dict[str, dict] = {}
    for row in rows:
        try:
            centroid = json.loads(row["centroid_json"])
            if not isinstance(centroid, list) or not centroid:
                continue
        except Exception:
            continue
        payload[str(row["arc_name"])] = {
            "centroid": [float(value) for value in centroid],
            "sample_count": float(row["sample_count"]),
            "dominant_topic": row["dominant_topic"],
            "vibe": row["vibe"],
            "strength": float(row["strength"] or 0.0),
        }
    return payload


def upsert_arc_centroids(user_id: str, centroid_updates: dict[str, dict]) -> None:
    if not centroid_updates:
        return

    now = utc_now_iso()
    with get_connection() as conn:
        for arc_name, payload in centroid_updates.items():
            conn.execute(
                """
                INSERT INTO arc_centroids (
                    user_id, arc_name, centroid_json, sample_count, dominant_topic, vibe, strength, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, arc_name)
                DO UPDATE SET
                    centroid_json = excluded.centroid_json,
                    sample_count = excluded.sample_count,
                    dominant_topic = excluded.dominant_topic,
                    vibe = excluded.vibe,
                    strength = excluded.strength,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    arc_name,
                    json.dumps(payload.get("centroid", [])),
                    float(payload.get("sample_count", 0.0)),
                    payload.get("dominant_topic"),
                    payload.get("vibe"),
                    float(payload.get("strength", 0.0)),
                    now,
                ),
            )
        conn.commit()


def get_wallpaper_memory(user_id: str, limit: int = 36) -> list[dict]:
    safe_limit = max(1, min(limit, 200))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT topic, vibe, style, provider, wallpaper_query, wallpaper_preview_url, created_at
            FROM wallpaper_memory
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, safe_limit),
        ).fetchall()
    return [
        {
            "topic": str(row["topic"]),
            "vibe": str(row["vibe"]),
            "style": str(row["style"]),
            "provider": str(row["provider"]),
            "wallpaper_query": str(row["wallpaper_query"]),
            "wallpaper_preview_url": row["wallpaper_preview_url"],
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]


def create_wallpaper_memory(
    *,
    user_id: str,
    topic: str,
    vibe: str,
    style: str,
    provider: str,
    wallpaper_query: str,
    wallpaper_preview_url: str | None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO wallpaper_memory (
                user_id, topic, vibe, style, provider, wallpaper_query, wallpaper_preview_url, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                topic,
                vibe,
                style,
                provider,
                wallpaper_query,
                wallpaper_preview_url,
                utc_now_iso(),
            ),
        )
        conn.commit()


def update_user_preference(user_id: str, target_type: str, target_key: str, action: str) -> None:
    delta_map = {
        "like": 1.0,
        "keep": 0.45,
        "skip": -0.6,
        "tone_down": -0.35,
    }
    delta = delta_map.get(action, 0.0)
    if not delta:
        return

    now = utc_now_iso()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT score
            FROM user_preferences
            WHERE user_id = ? AND target_type = ? AND target_key = ?
            """,
            (user_id, target_type, target_key),
        ).fetchone()
        if row is None:
            score = delta
            conn.execute(
                """
                INSERT INTO user_preferences (user_id, target_type, target_key, score, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, target_type, target_key, score, now),
            )
        else:
            score = max(-4.0, min(4.0, float(row["score"]) * 0.92 + delta))
            conn.execute(
                """
                UPDATE user_preferences
                SET score = ?, updated_at = ?
                WHERE user_id = ? AND target_type = ? AND target_key = ?
                """,
                (score, now, user_id, target_type, target_key),
            )
        conn.commit()


def get_user_preference_profile(user_id: str) -> dict[str, dict[str, float]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT target_type, target_key, score
            FROM user_preferences
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()

    profile: dict[str, dict[str, float]] = {}
    for row in rows:
        target_type = str(row["target_type"])
        bucket = profile.setdefault(target_type, {})
        bucket[str(row["target_key"])] = round(float(row["score"]), 4)
    return profile
