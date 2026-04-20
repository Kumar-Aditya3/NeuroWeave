import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data.db"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"

TOPICS = ["tech", "anime", "fitness", "philosophy", "self-help", "news"]


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
        conn.commit()


def create_event(
    *,
    user_id: str,
    source: str,
    event_type: str,
    url: str | None,
    title: str | None,
    selected_text: str | None,
    content_text: str | None,
    topic_scores: Dict[str, float],
    sentiment: str,
    vibe: str,
    created_at: str,
) -> int:
    payload = {
        "user_id": user_id,
        "source": source,
        "event_type": event_type,
        "url": url,
        "title": title,
        "selected_text": selected_text,
        "content_text": content_text,
        "topic_scores_json": json.dumps(topic_scores),
        "sentiment": sentiment,
        "vibe": vibe,
        "created_at": created_at,
    }
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO events (
                user_id, source, event_type, url, title, selected_text,
                content_text, topic_scores_json, sentiment, vibe, created_at
            )
            VALUES (
                :user_id, :source, :event_type, :url, :title, :selected_text,
                :content_text, :topic_scores_json, :sentiment, :vibe, :created_at
            )
            """,
            payload,
        )
        conn.commit()
        return int(cursor.lastrowid)


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


def create_feedback(user_id: str, recommendation_topic: str, action: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO feedback (user_id, recommendation_topic, action, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, recommendation_topic, action, utc_now_iso()),
        )
        conn.commit()
