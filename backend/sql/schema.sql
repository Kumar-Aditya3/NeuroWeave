CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    url TEXT,
    title TEXT,
    selected_text TEXT,
    content_text TEXT,
    topic_scores_json TEXT NOT NULL,
    sentiment TEXT NOT NULL,
    vibe TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profile_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    window TEXT NOT NULL,
    topic TEXT NOT NULL,
    score REAL NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, window, topic)
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    recommendation_topic TEXT NOT NULL,
    action TEXT NOT NULL,
    created_at TEXT NOT NULL
);
