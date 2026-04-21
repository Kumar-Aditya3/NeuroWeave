import ctypes
from ctypes import wintypes

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


def get_process_name(process_id: int) -> str:
    try:
        import psutil

        return psutil.Process(process_id).name()
    except Exception:
        return "unknown"


def is_sensitive_title(title: str) -> bool:
    lowered = title.lower()
    return any(hint in lowered for hint in SENSITIVE_TITLE_HINTS)


def ocr_active_window(hwnd: int) -> str:
    try:
        from PIL import ImageGrab
        import pytesseract
    except Exception:
        return ""

    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return ""

    bbox = (rect.left, rect.top, rect.right, rect.bottom)
    if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
        return ""

    image = ImageGrab.grab(bbox=bbox)
    try:
        text = pytesseract.image_to_string(image)
    except Exception:
        return ""
    finally:
        image.close()
    return " ".join(text.split())
