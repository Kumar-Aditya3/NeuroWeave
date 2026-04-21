# NeuroWeave Capture Notes

## The Idea

Every collector is just a small program that notices one kind of activity and sends the same basic shape to the backend:

```json
{
  "user_id": "kumar",
  "device_id": "one-stable-id-per-pc",
  "client_name": "Main PC",
  "source": "active_window",
  "event_type": "active_window",
  "title": "Window title",
  "content_text": "optional text",
  "timestamp": "2026-04-21T10:00:00Z"
}
```

`user_id` merges everything into one identity. `device_id` keeps each PC/browser separate for debugging.

## Backend Syntax

FastAPI endpoints are Python functions with decorators:

```python
@app.post("/ingest/activity")
def ingest_activity(payload: ActivityIngestRequest):
    ...
```

The decorator says which URL calls the function. The Pydantic model (`ActivityIngestRequest`) defines the JSON fields the backend accepts.

## Extension Syntax

The extension listens to browser tab events:

```javascript
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete") {
    sendTabEvent(tab);
  }
});
```

Then it uses `fetch()` to POST JSON to the backend.

## Agent Syntax

The Windows agent loops every few seconds:

```python
while True:
    window = get_active_window()
    post_activity(config, payload)
    time.sleep(interval)
```

That is the collector pattern: observe, normalize, send, wait.

## Dedupe

Repeated activity can inflate your profile. The backend makes a `dedupe_key` from:

- user
- device
- event type
- title
- five-minute time bucket

If the same event arrives again in the same bucket, it is stored once and does not update the profile again.
