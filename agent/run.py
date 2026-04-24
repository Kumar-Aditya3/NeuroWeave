import json
import platform
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .app_catalog import categorize_app
from .config import load_config
from .windows_capture import get_active_window, is_sensitive_title, ocr_active_window

BLOCKED_PROCESS_NAMES = {
    "credentialui.exe",
    "lockapp.exe",
    "logonui.exe",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def post_activity(config: dict, payload: dict) -> bool:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        f"{config['backend_url'].rstrip('/')}/ingest/activity",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": config["api_key"],
        },
    )
    try:
        with urlopen(request, timeout=8) as response:
            return 200 <= response.status < 300
    except HTTPError as error:
        print(f"Backend rejected event: {error.code} {error.reason}")
    except URLError as error:
        print(f"Backend unreachable: {error.reason}")
    except TimeoutError:
        print("Backend request timed out")
    return False


def post_activity_cloud(config: dict, payload: dict) -> bool:
    if not config.get("cloud_ingest_enabled"):
        return False
    ingest_url = (config.get("cloud_ingest_url") or "").strip()
    if not ingest_url:
        return False

    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
    }
    if config.get("cloud_ingest_key"):
        headers["X-Ingest-Key"] = str(config.get("cloud_ingest_key"))

    request = Request(
        ingest_url,
        data=body,
        method="POST",
        headers=headers,
    )
    try:
        with urlopen(request, timeout=8) as response:
            return 200 <= response.status < 300
    except HTTPError as error:
        print(f"Cloud ingest rejected event: {error.code} {error.reason}")
    except URLError as error:
        print(f"Cloud ingest unreachable: {error.reason}")
    except TimeoutError:
        print("Cloud ingest request timed out")
    return False


def post_activity_with_fallback(config: dict, payload: dict) -> bool:
    if post_activity(config, payload):
        return True
    return post_activity_cloud(config, payload)


def build_activity_payload(config: dict, window: dict) -> dict | None:
    title = (window.get("title") or "").strip()
    process_name = (window.get("process_name") or "unknown").strip()
    if not title or process_name.lower() in BLOCKED_PROCESS_NAMES:
        return None
    if is_sensitive_title(title):
        return None

    category, inferred_kind = categorize_app(process_name, title)
    event_type = "game" if inferred_kind == "game" else "active_window"
    return {
        "user_id": config["user_id"],
        "device_id": config["device_id"],
        "client_name": config["client_name"],
        "source": event_type,
        "event_type": event_type,
        "title": title,
        "process_name": process_name,
        "category": category,
        "timestamp": now_iso(),
    }


def maybe_send_ocr(config: dict, window: dict) -> None:
    if not config.get("ocr_enabled"):
        return
    if config.get("ocr_mode") != "active_window_only":
        return
    if is_sensitive_title(window.get("title", "")):
        return

    text = ocr_active_window(int(window.get("hwnd", 0)))
    if not text:
        return

    payload = {
        "user_id": config["user_id"],
        "device_id": config["device_id"],
        "client_name": config["client_name"],
        "source": "ocr_text",
        "event_type": "ocr_text",
        "title": window.get("title") or "OCR text",
        "content_text": text[:4000],
        "process_name": window.get("process_name", "unknown"),
        "category": "ocr",
        "timestamp": now_iso(),
    }
    post_activity_with_fallback(config, payload)


def main() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("The first NeuroWeave agent only supports Windows.")

    config = load_config()
    print(f"NeuroWeave agent running as {config['client_name']} ({config['device_id']})")
    last_activity_key = ""

    while True:
        if config.get("active_app_enabled", True):
            window = get_active_window()
            payload = build_activity_payload(config, window)
            if payload:
                activity_key = "|".join(
                    [
                        payload["event_type"],
                        payload.get("category", ""),
                        payload["title"],
                        payload.get("process_name", ""),
                    ]
                )
                if activity_key != last_activity_key:
                    if post_activity_with_fallback(config, payload):
                        print(f"Sent {payload['event_type']}: {payload['title']}")
                    last_activity_key = activity_key
                maybe_send_ocr(config, window)

        time.sleep(max(5, int(config.get("interval_seconds", 20))))


if __name__ == "__main__":
    main()
