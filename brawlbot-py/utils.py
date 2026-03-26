import re
from datetime import datetime


def normalize_tag(tag: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", tag).upper()
    return f"#{cleaned}"


def parse_battle_time(time_str: str) -> datetime:
    formatted = re.sub(
        r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})",
        r"\1-\2-\3T\4:\5:\6",
        time_str,
    )
    return datetime.fromisoformat(formatted.replace("Z", "+00:00"))


def time_diff_minutes(time1: str, time2: str) -> float:
    d1 = parse_battle_time(time1)
    d2 = parse_battle_time(time2)
    return abs((d1 - d2).total_seconds()) / 60


def result_emoji(result: str) -> str:
    return {"victory": "\U0001f7e2", "defeat": "\U0001f534"}.get(result, "\u26aa")


MODE_EMOJIS = {
    "gemGrab": "\U0001f48e",
    "brawlBall": "\u26bd",
    "heist": "\U0001f510",
    "bounty": "\u2b50",
    "siege": "\U0001f527",
    "hotZone": "\U0001f525",
    "knockout": "\U0001f480",
    "wipeout": "\U0001f4a5",
    "payload": "\U0001f69b",
    "snowtelThieves": "\u2744\ufe0f",
    "paintBrawl": "\U0001f3a8",
    "trophy_thieves": "\U0001f3c6",
}


def mode_emoji(mode: str) -> str:
    return MODE_EMOJIS.get(mode, "\U0001f3ae")


def format_win_rate(wins: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{(wins / total) * 100:.1f}%"


def format_mode_name(mode: str) -> str:
    # Insert space before uppercase letters (camelCase -> Title Case)
    spaced = re.sub(r"([A-Z])", r" \1", mode)
    return spaced.strip().title()
