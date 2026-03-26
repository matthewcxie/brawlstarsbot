import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
GUILD_ID = os.getenv("GUILD_ID")
BRAWL_API_KEY = os.getenv("BRAWL_API_KEY")
RESULTS_CHANNEL_IDS = [
    cid.strip()
    for cid in (os.getenv("RESULTS_CHANNEL_IDS") or os.getenv("RESULTS_CHANNEL_ID") or "").split(",")
    if cid.strip()
]
MYTHIC_PASSWORD = os.getenv("MYTHIC_PASSWORD")
PIC_ADMIN_ID = os.getenv("PIC_ADMIN_ID")
PIC_STORAGE_CHANNEL_ID = os.getenv("PIC_STORAGE_CHANNEL_ID")
PIC_CHANNEL_ID = os.getenv("PIC_CHANNEL_ID")

SET_TIME_GAP_MINUTES = 5
STALE_SET_MINUTES = 30
