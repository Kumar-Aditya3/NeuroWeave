# NeuroWeave Backend

## Goal

NeuroWeave builds a context-aware personalization engine that adapts a user's digital environment based on what they are consuming.  
Current focus is desktop-first and opt-in: ingest user-approved content signals, build a lightweight evolving profile, and generate recommendations for wallpaper mood, music mood, and quote style.

## Current Methods

### Data Ingestion

- Browser event ingestion via `POST /ingest/page` (URL, title, selected text, timestamp, `device_id`, `client_name`)
- PDF text ingestion via `POST /ingest/pdf` (parsed text payload, `device_id`, `client_name`)
- Generic activity ingestion via `POST /ingest/activity`
- Feedback capture via `POST /feedback` (`keep`, `skip`, `like`)
- Source visibility via `GET /me/sources`
- Recent activity debugging via `GET /me/recent-events`
- Dashboard aggregation via `GET /me/dashboard`

### Content Understanding

- Keyword-based topical scoring across:
  - `tech`, `education`, `anime`, `fitness`, `philosophy`, `self-help`, `news`, `unknown`
- Unknown content is tracked as `unknown` instead of being forced into a topic.
- Semantic anchor embeddings are now the primary classifier path, with keyword mode kept as a fallback/debug mode.
- Basic sentiment detection (`positive`, `neutral`, `negative`)
- Basic vibe detection (`calm`, `balanced`, `intense`, `dark`)

### User Profile Modeling

- SQLite-backed event store and profile tables
- Device registry table for cross-device source tracking
- Event dedupe over short time buckets to reduce repeated profile inflation
- Dual preference windows:
  - `short_term` profile with faster decay
  - `long_term` profile with slower decay
- Weighted profile merge for current preference state

### Output Engine

- Context recommendation endpoint: `GET /recommend/context`
- Dashboard aggregation via `GET /me/dashboard` now carries wallpaper preview/query metadata
- Rule-based mapping from dominant topic + latest vibe to:
  - wallpaper tags
  - music mood
  - quote style

### Access Control

- API-key protected ingestion and recommendation endpoints using `X-API-Key`
- Valid keys are configured via `NEUROWEAVE_API_KEYS` (comma-separated)

## Local Collectors

### Browser Extension

The `extension/` folder contains a shared Chromium extension for Chrome and Opera GX.

- Load it as an unpacked extension.
- Set the same `user_id` on every browser, usually `kumar`.
- Give each browser/device a clear `client_name`.
- Turn tracking on only when you want tab activity sent.

### Windows Agent

The `agent/` folder contains the first desktop collector.

```bash
pip install -r agent/requirements.txt
python -m agent.run
```

On first run it creates `agent/config.local.json` with a persistent `device_id`.

- `active_app_enabled` tracks active window titles and process names.
- `ocr_enabled` is off by default.
- OCR reads only the active window and sends extracted text, not screenshots.

### Stack

- API: FastAPI
- Data store: SQLite
- Language: Python

## Supabase Cloud Mirror (Optional)

You can keep local SQLite for fast local reads while mirroring ingest data to Supabase.

### 1) Create tables in Supabase

Run [sql/supabase_bootstrap.sql](sql/supabase_bootstrap.sql) in the Supabase SQL editor.

This creates:

- `events_raw`
- `devices_state`
- `feedback_events`
- `wallpaper_memory`
- `arc_centroids`
- retention function + daily `pg_cron` job

### 2) Configure backend environment

Copy values from [.env.supabase.example](.env.supabase.example) into your runtime environment:

- `NEUROWEAVE_SUPABASE_ENABLED=true`
- `NEUROWEAVE_SUPABASE_URL=<your-project-url>`
- `NEUROWEAVE_SUPABASE_SERVICE_ROLE_KEY=<service-role-key>`

Use the Service Role key for backend server-to-server writes.
Do not use the publishable/anon key for backend ingestion writes.

### 3) Behavior

When Supabase mirror is enabled, these endpoints also write to Supabase:

- `POST /ingest/page`
- `POST /ingest/pdf`
- `POST /ingest/activity`
- `POST /feedback`

If Supabase credentials are missing or request fails, local SQLite ingestion still succeeds.
