# Android Ingestion Plan

NeuroWeave already accepts future mobile events through `POST /ingest/activity` with these source types:

- `mobile_share`
- `mobile_app`
- `mobile_media`

## Phase 1

Use Android share intent to send text, links, and article titles into NeuroWeave. The first native watcher lives in `android_watcher/`.

Payload shape:

```json
{
  "user_id": "kumar",
  "device_id": "android-device-id",
  "client_name": "Pixel 8",
  "source": "mobile_share",
  "event_type": "mobile_share",
  "title": "Shared from Android",
  "url": "https://example.com/article",
  "content_text": "Optional article excerpt or highlighted text",
  "category": "mobile_share"
}
```

## Phase 2

Add optional app-usage ingestion where Android permissions allow it. `android_watcher` uses Usage Access to report foreground-app sessions with `duration_seconds`.

Examples:

- `source=mobile_app` for foreground-app usage summaries
- `source=mobile_media` for media session metadata

Suggested normalized categories:

- `study`
- `coding`
- `media`
- `communication`
- `gaming`
- `browsing`

## Guardrails

- Keep phone ingestion opt-in.
- Prefer text, titles, and app labels over screenshots.
- Reuse the same `user_id` across all PCs and the phone so the profile stays unified.
- Keep `device_id` stable per device.
