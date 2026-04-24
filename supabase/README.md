# Supabase Direct Ingest Setup

This folder contains an Edge Function for direct event ingestion into Supabase when the NeuroWeave backend is offline.

## Edge Function

Function path: `functions/ingest-event/index.ts`

It expects:

- Method: `POST`
- Header: `X-Ingest-Key: <NEUROWEAVE_INGEST_KEY>`
- JSON body fields:
  - required: `user_id`, `source`, `event_type`
  - optional: `device_id`, `client_name`, `title`, `url`, `category`, `selected_text`, `content_text`, `process_name`, `timestamp`

## Deploy

Use `npx supabase` to avoid PATH issues on Windows.

1. Create a Supabase personal access token in dashboard:

- Account Settings -> Access Tokens -> Generate token

2. Set token in shell:

```powershell
$env:SUPABASE_ACCESS_TOKEN = "replace_with_personal_access_token"
```

3. Link project:

```bash
npx supabase link --project-ref xfffhfiefspczxhpeszu
```

4. Set function secret (shared by clients):

```bash
npx supabase secrets set NEUROWEAVE_INGEST_KEY=replace_with_long_random_key --project-ref xfffhfiefspczxhpeszu
```

5. Deploy function:

```bash
npx supabase functions deploy ingest-event --project-ref xfffhfiefspczxhpeszu
```

Function URL:

`https://xfffhfiefspczxhpeszu.supabase.co/functions/v1/ingest-event`

6. Smoke test function:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "https://xfffhfiefspczxhpeszu.supabase.co/functions/v1/ingest-event" `
  -Headers @{ "x-ingest-key" = "replace_with_long_random_key" } `
  -ContentType "application/json" `
  -Body '{"user_id":"kumar","device_id":"desktop-cli-test","client_name":"Desktop CLI Test","source":"active_window","event_type":"active_window","title":"CLI deploy smoke test","content_text":"supabase function invoke test"}'
```

## Client Wiring

### Windows Agent (`agent/config.local.json`)

Set:

```json
{
  "cloud_ingest_enabled": true,
  "cloud_ingest_url": "https://xfffhfiefspczxhpeszu.supabase.co/functions/v1/ingest-event",
  "cloud_ingest_key": "replace_with_long_random_key"
}
```

### Browser Extension

In popup settings:

- Enable `Cloud fallback ingest`
- Set `Cloud ingest URL`
- Set `Cloud ingest key`

The extension tries backend first, then falls back to cloud ingest.
