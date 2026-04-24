from __future__ import annotations

import ctypes
import json
import os
import platform
import socket
import sys
import time
import uuid
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

APP_NAME = "NeuroWeave Portable Agent"
BLOCKED_PROCESS_NAMES = {
    "credentialui.exe",
    "lockapp.exe",
    "logonui.exe",
}
GAME_HINTS = {
    "steam.exe",
    "epicgameslauncher.exe",
    "riotclientservices.exe",
    "valorant-win64-shipping.exe",
    "fortniteclient-win64-shipping.exe",
    "minecraftlauncher.exe",
    "minecraft.exe",
    "robloxplayerbeta.exe",
    "cs2.exe",
    "gta5.exe",
}
SENSITIVE_TITLE_HINTS = {"password", "signin", "sign in", "login", "otp", "bank"}

APP_RULES = [
    {"processes": {"code.exe", "pycharm64.exe", "idea64.exe", "devenv.exe"}, "category": "coding", "kind": "active_window"},
    {"processes": {"powershell.exe", "cmd.exe", "windows terminal.exe", "wt.exe"}, "category": "coding", "kind": "active_window"},
    {"processes": {"notion.exe", "obsidian.exe", "onenote.exe", "notepad.exe"}, "category": "study", "kind": "active_window"},
    {"processes": {"spotify.exe", "vlc.exe", "music.ui.exe"}, "category": "media", "kind": "active_window"},
    {"processes": {"discord.exe", "slack.exe", "telegram.exe", "whatsapp.exe"}, "category": "communication", "kind": "active_window"},
    {"processes": {"chrome.exe", "opera.exe", "opera_gx.exe", "msedge.exe", "firefox.exe"}, "category": "browsing", "kind": "active_window"},
    {
        "processes": {
            "steam.exe",
            "epicgameslauncher.exe",
            "valorant-win64-shipping.exe",
            "fortniteclient-win64-shipping.exe",
            "minecraft.exe",
            "robloxplayerbeta.exe",
            "cs2.exe",
            "gta5.exe",
        },
        "category": "gaming",
        "kind": "game",
    },
]

TITLE_HINTS = [
    {"contains": ["visual studio code", "pycharm", "terminal", "powershell"], "category": "coding", "kind": "active_window"},
    {"contains": ["lecture", "course", "assignment", "study", "notes"], "category": "study", "kind": "active_window"},
    {"contains": ["youtube", "spotify", "netflix"], "category": "media", "kind": "active_window"},
    {"contains": ["discord", "slack", "chat"], "category": "communication", "kind": "active_window"},
    {"contains": ["valorant", "minecraft", "counter-strike", "fortnite"], "category": "gaming", "kind": "game"},
]


def _base_dir() -> Path:
    if getattr(__import__("sys"), "frozen", False):
        return Path(__import__("sys").executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = _base_dir()
CONFIG_PATH = BASE_DIR / "portable_agent.config.json"
QUEUE_PATH = BASE_DIR / "portable_agent.queue.jsonl"

DEFAULT_CONFIG = {
    "user_id": "kumar",
    "device_id": "",
    "client_name": "",
    "interval_seconds": 12,
    "ingest_url": "https://xfffhfiefspczxhpeszu.supabase.co/functions/v1/ingest-event",
    "ingest_key": "",
    "max_queue_items": 2000,
    "flush_batch_size": 10,
    "run_on_startup": True,
    "startup_entry_name": "NeuroWeave Portable Agent",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_process_name(process_id: int) -> str:
    try:
        import psutil

        return psutil.Process(process_id).name()
    except Exception:
        return "unknown"


def get_active_window() -> dict:
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return {"title": "", "process_id": 0, "process_name": "unknown", "category": "unknown"}

    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    process_name = get_process_name(pid.value)
    category = "game" if process_name.lower() in GAME_HINTS else "active_window"

    return {
        "title": buffer.value,
        "process_id": int(pid.value),
        "process_name": process_name,
        "category": category,
        "hwnd": int(hwnd),
    }


def is_sensitive_title(title: str) -> bool:
    lowered = title.lower()
    return any(hint in lowered for hint in SENSITIVE_TITLE_HINTS)


def categorize_app(process_name: str, title: str) -> tuple[str, str]:
    lowered_process = process_name.lower()
    lowered_title = title.lower()

    for rule in APP_RULES:
        if lowered_process in rule["processes"]:
            return rule["category"], rule["kind"]

    for rule in TITLE_HINTS:
        if any(fragment in lowered_title for fragment in rule["contains"]):
            return rule["category"], rule["kind"]

    return "general", "active_window"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    else:
        data = DEFAULT_CONFIG.copy()

    changed = False
    if not data.get("device_id"):
        data["device_id"] = str(uuid.uuid4())
        changed = True
    if not data.get("client_name"):
        data["client_name"] = socket.gethostname()
        changed = True

    for key, value in DEFAULT_CONFIG.items():
        if key not in data:
            data[key] = value
            changed = True

    if changed or not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def _startup_cmd_path(entry_name: str) -> Path:
    appdata = Path(os.environ.get("APPDATA", ""))
    startup_dir = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch for ch in entry_name if ch.isalnum() or ch in {" ", "-", "_"}).strip() or "NeuroWeave"
    return startup_dir / f"{safe_name}.cmd"


def ensure_startup_registration(config: dict) -> None:
    entry_name = str(config.get("startup_entry_name", "NeuroWeave Portable Agent"))
    cmd_path = _startup_cmd_path(entry_name)
    run_on_startup = bool(config.get("run_on_startup", True))

    if getattr(sys, "frozen", False):
        launch_target = Path(sys.executable).resolve()
        launch_line = f'start "" "{launch_target}"'
    else:
        launch_target = Path(__file__).resolve()
        launch_line = f'start "" "{Path(sys.executable).resolve()}" "{launch_target}"'

    if run_on_startup:
        cmd_path.write_text(
            "@echo off\n"
            "REM Auto-generated by NeuroWeave Portable Agent\n"
            f"{launch_line}\n",
            encoding="utf-8",
        )
    else:
        if cmd_path.exists():
            cmd_path.unlink()


def _post_event(ingest_url: str, ingest_key: str, payload: dict) -> bool:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
    }
    if ingest_key:
        headers["X-Ingest-Key"] = ingest_key

    request = Request(ingest_url, data=body, method="POST", headers=headers)
    try:
        with urlopen(request, timeout=8) as response:
            return 200 <= response.status < 300
    except HTTPError as error:
        print(f"Ingest rejected event: {error.code} {error.reason}")
    except URLError as error:
        print(f"Ingest unreachable: {error.reason}")
    except TimeoutError:
        print("Ingest request timed out")
    return False


def _append_queue(items: list[dict]) -> None:
    if not items:
        return
    with QUEUE_PATH.open("a", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=True) + "\n")


def _read_queue() -> list[dict]:
    if not QUEUE_PATH.exists():
        return []
    rows: list[dict] = []
    for line in QUEUE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
        except Exception:
            continue
    return rows


def _write_queue(items: list[dict], max_items: int) -> None:
    trimmed = items[-max(1, int(max_items)) :]
    if not trimmed:
        if QUEUE_PATH.exists():
            QUEUE_PATH.unlink()
        return
    QUEUE_PATH.write_text(
        "\n".join(json.dumps(item, ensure_ascii=True) for item in trimmed) + "\n",
        encoding="utf-8",
    )


def _enqueue(payload: dict, max_items: int) -> None:
    queue = _read_queue()
    queue.append(payload)
    _write_queue(queue, max_items=max_items)


def flush_queue(config: dict) -> None:
    queue = _read_queue()
    if not queue:
        return

    batch_size = max(1, int(config.get("flush_batch_size", 10)))
    ingest_url = str(config.get("ingest_url", "")).strip()
    ingest_key = str(config.get("ingest_key", "")).strip()

    sent_count = 0
    remaining: list[dict] = []
    for index, payload in enumerate(queue):
        if sent_count >= batch_size:
            remaining.extend(queue[index:])
            break
        if _post_event(ingest_url, ingest_key, payload):
            sent_count += 1
        else:
            remaining.extend(queue[index:])
            break

    _write_queue(remaining, max_items=int(config.get("max_queue_items", 2000)))
    if sent_count:
        print(f"Flushed {sent_count} queued event(s)")


def build_payload(config: dict, window: dict) -> dict | None:
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


def main() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("NeuroWeave portable agent supports Windows only")

    config = load_config()
    ensure_startup_registration(config)
    print(f"{APP_NAME} running as {config['client_name']} ({config['device_id']})")
    if not config.get("ingest_key"):
        print("WARNING: ingest_key is empty in portable_agent.config.json")

    last_activity_key = ""
    while True:
        flush_queue(config)

        window = get_active_window()
        payload = build_payload(config, window)
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
                ingest_url = str(config.get("ingest_url", "")).strip()
                ingest_key = str(config.get("ingest_key", "")).strip()
                ok = _post_event(ingest_url, ingest_key, payload)
                if ok:
                    print(f"Sent {payload['event_type']}: {payload['title']}")
                else:
                    _enqueue(payload, max_items=int(config.get("max_queue_items", 2000)))
                    print("Queued event due to ingest outage")
                last_activity_key = activity_key

        time.sleep(max(4, int(config.get("interval_seconds", 12))))


if __name__ == "__main__":
    main()
