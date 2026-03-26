import aiohttp
from urllib.parse import quote
from config import BRAWL_API_KEY

BASE_URL = "https://api.brawlstars.com/v1"


class BrawlAPIError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)


async def _api_fetch(endpoint: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {BRAWL_API_KEY}"},
        ) as resp:
            if not resp.ok:
                body = await resp.text()
                raise BrawlAPIError(resp.status, f"Brawl Stars API {resp.status}: {resp.reason} - {body}")
            return await resp.json()


async def get_player(tag: str):
    return await _api_fetch(f"/players/{quote(tag)}")


async def get_battle_log(tag: str) -> list:
    data = await _api_fetch(f"/players/{quote(tag)}/battlelog")
    return data.get("items", [])


async def get_brawlers() -> list:
    data = await _api_fetch("/brawlers")
    return data.get("items", [])
