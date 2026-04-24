# Supabase Direct Ingest Setup

This folder contains an Edge Function that allows PC/mobile clients to ingest events directly into Supabase when the NeuroWeave backend is offline.

## Edge Function

Function path: `functions/ingest-event/index.ts`

It expects:

- Method: `POST`
- Header: `X-Ingest-Key: <NEUROWEAVE_INGEST_KEY>`
- JSON body fields:
  - required: `user_id`, `source`, `event_type`
  - optional: `device_id`, `client_name`, `title`, `url`, `category`, `selected_text`, `content_text`, `process_name`, `timestamp`

## Deploy

1. Install Supabase CLI and login.
2. Link project:

```bash
supabase link --project-ref xfffhfiefspczxhpeszu
```

3. Set function secret (shared by clients):

```bash
supabase secrets set NEUROWEAVE_INGEST_KEY=replace_with_long_random_key
```

4. Deploy function:

```bash
supabase functions deploy ingest-event
```

Function URL:

`https://xfffhfiefspczxhpeszu.supabase.co/functions/v1/ingest-event`

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

The extension tries backend first, then cloud ingest fallback.
