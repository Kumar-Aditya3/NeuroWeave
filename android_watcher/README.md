# NeuroWeave Android Watcher

This is the first Android collector for NeuroWeave. It sends phone activity into the same `user_id` profile as the desktop agents.

## What It Captures

- Manual shares through Android's share sheet as `mobile_share`
- Foreground app sessions through Android Usage Access as `mobile_app`
- Media-heavy app sessions as `mobile_media`
- Session duration through `duration_seconds`

It does not capture screenshots, keystrokes, passwords, or notification contents.

## Setup

Open `android_watcher/` in Android Studio and run the `app` configuration.

In the app:

- Set `User ID` to `kumar`
- Set a device name, such as `Pixel Phone`
- Set `Ingest URL`
- Set `Ingest key`
- Use `X-Ingest-Key` for Supabase Edge Function ingestion
- Use `X-API-Key` if pointing directly at the local FastAPI backend
- Tap `Open Usage Access` and enable NeuroWeave Watcher
- Enable `Watch foreground apps`

## Recommended Ingest URL

For always-on cross-device capture, use the Supabase Edge Function:

```text
https://xfffhfiefspczxhpeszu.supabase.co/functions/v1/ingest-event
```

## Event Contract

The watcher sends events to `POST /ingest/activity` compatible endpoints:

```json
{
  "user_id": "kumar",
  "device_id": "stable-android-device-id",
  "client_name": "Pixel Phone",
  "source": "mobile_app",
  "event_type": "mobile_app",
  "title": "YouTube",
  "category": "media",
  "process_name": "com.google.android.youtube",
  "content_text": "media mobile session in YouTube",
  "duration_seconds": 120
}
```

## Notes

Android does not expose full browsing/app content like a desktop browser extension. The watcher intentionally starts with app sessions and manual shares, which are useful signals without crossing into invasive capture.
