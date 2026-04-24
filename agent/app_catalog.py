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
