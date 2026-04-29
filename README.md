# NeuroWeave

NeuroWeave is a context-aware personalization stack that ingests opt-in activity from multiple devices, builds short-term and long-term preference signals, and generates adaptive recommendations such as desktop wallpaper mood.

## 🚀 Quick Start (Portable Setup)

Want to get started quickly? Just copy the folder to another PC:

1. **Copy `NeuroWeave` folder** to target PC
2. **Run `setup_portable.bat`** (one time, 5-15 minutes)
3. **Run `run_all.bat`** to start everything

See [QUICK_START.md](QUICK_START.md) for details, or [PORTABLE_SETUP.md](PORTABLE_SETUP.md) for comprehensive guide.

## Repository Layout

- `backend/`: FastAPI service, profile logic, recommendations, Supabase mirror support.
- `agent/`: Windows desktop collector.
- `portable_agent/`: standalone portable collector with local queue + startup support.
- `desktop/`: Electron desktop console.
- `extension/`: browser collector extension.
- `supabase/`: Edge Function and deployment docs for direct cloud ingest.

## Quick Start (Development)

### 1) Backend

Run from repository root on Windows:

```bat
start_backend.bat
```

Backend default URL:

- `http://127.0.0.1:8000`

### 2) Portable Collector

Build the standalone executable:

```bat
portable_agent\build_portable_agent.bat
```

Output:

- `dist\neuroweave_portable_agent.exe`

Place next to a `portable_agent.config.json` file (see `portable_agent/portable_agent.config.example.json`).

### 3) Supabase Direct Ingest

See setup and deployment steps in:

- `supabase/README.md`

## Notes

- Collectors can keep ingesting even when backend is offline by posting to Supabase Edge Function.
- Retention and cleanup are handled by SQL bootstrap logic in `backend/sql/supabase_bootstrap.sql`.
- Keep service keys and ingest keys out of git.
