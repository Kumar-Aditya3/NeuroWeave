CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    device_id TEXT,
    client_name TEXT,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    url TEXT,
    title TEXT,
    category TEXT,
    selected_text TEXT,
    content_text TEXT,
    topic_scores_json TEXT NOT NULL,
    embedding_json TEXT,
    classifier_mode TEXT,
    sentiment TEXT NOT NULL,
    vibe TEXT NOT NULL,
    created_at TEXT NOT NULL,
    dedupe_key TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    client_name TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE (user_id, device_id)
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
);

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
);

CREATE INDEX IF NOT EXISTS idx_wallpaper_memory_user_created
ON wallpaper_memory(user_id, created_at DESC);
