# NeuroWeave Portable Agent

A lightweight Windows background collector that sends activity events directly to Supabase Edge Function ingest.

## What it does

- Captures active window title + process name.
- Classifies category using existing app catalog rules.
- Sends events to cloud ingest endpoint.
- Stores unsent events in a local queue file and retries automatically.
- Runs independently from backend process.
- Auto-registers itself for Windows startup (configurable).

## Build EXE

From repo root on Windows:

```bat
portable_agent\build_portable_agent.bat
```

Output executable:

`dist\neuroweave_portable_agent.exe`

## First run

Run the executable once. It creates:

`portable_agent.config.json`

in the same folder as the executable.

You can also start from:

`portable_agent.config.example.json`

Update these fields:

- `user_id`
- `ingest_url`
- `ingest_key`

Startup controls:

- `run_on_startup`: set `true` to auto-launch on Windows sign-in.
- `startup_entry_name`: startup entry label used in Startup folder.

Recommended `ingest_url`:

`https://xfffhfiefspczxhpeszu.supabase.co/functions/v1/ingest-event`

## Portable files to carry

- `neuroweave_portable_agent.exe`
- `portable_agent.config.json`
- `portable_agent.queue.jsonl` (created automatically if offline)

## Notes

- If ingest is down, events are queued in `portable_agent.queue.jsonl` and flushed later.
- Queue size is capped by `max_queue_items` in config.
- Agent skips known sensitive window titles and blocked system processes.
- Startup launcher file is created under `%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup`.
