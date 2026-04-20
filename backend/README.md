# NeuroWeave Backend

## Goal

NeuroWeave builds a context-aware personalization engine that adapts a user's digital environment based on what they are consuming.  
Current focus is desktop-first and opt-in: ingest user-approved content signals, build a lightweight evolving profile, and generate recommendations for wallpaper mood, music mood, and quote style.

## Current Methods

### Data Ingestion

- Browser event ingestion via `POST /ingest/page` (URL, title, selected text, timestamp)
- PDF text ingestion via `POST /ingest/pdf` (parsed text payload)
- Feedback capture via `POST /feedback` (`keep`, `skip`, `like`)

### Content Understanding

- Keyword-based topical scoring across:
  - `tech`, `anime`, `fitness`, `philosophy`, `self-help`, `news`
- Basic sentiment detection (`positive`, `neutral`, `negative`)
- Basic vibe detection (`calm`, `balanced`, `intense`, `dark`)

### User Profile Modeling

- SQLite-backed event store and profile tables
- Dual preference windows:
  - `short_term` profile with faster decay
  - `long_term` profile with slower decay
- Weighted profile merge for current preference state

### Output Engine

- Context recommendation endpoint: `GET /recommend/context`
- Rule-based mapping from dominant topic + latest vibe to:
  - wallpaper tags
  - music mood
  - quote style

### Stack

- API: FastAPI
- Data store: SQLite
- Language: Python
