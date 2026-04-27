import json
import socket
import uuid
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).with_name("config.local.json")

DEFAULT_CONFIG = {
    "user_id": "kumar",
    "device_id": "",
    "client_name": "",
    "backend_url": "http://127.0.0.1:8000",
    "api_key": "dev-local-key",
    "interval_seconds": 20,
    "min_duration_seconds": 4,
    "browser_enabled": False,
    "active_app_enabled": True,
    "ocr_enabled": False,
    "ocr_mode": "active_window_only",
    "mobile_share_enabled": False,
    "cloud_ingest_enabled": False,
    "cloud_ingest_url": "",
    "cloud_ingest_key": "",
}


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    else:
        config = DEFAULT_CONFIG.copy()

    changed = False
    if not config.get("device_id"):
        config["device_id"] = str(uuid.uuid4())
        changed = True
    if not config.get("client_name"):
        config["client_name"] = socket.gethostname()
        changed = True

    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value
            changed = True

    if changed or not CONFIG_PATH.exists():
        save_config(config)
    return config


def save_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(
        json.dumps(config, indent=2, sort_keys=True),
        encoding="utf-8",
    )
