import time
import aiohttp

BRAWLAPI_MAPS_URL = "https://api.brawlapi.com/v1/maps"
BRAWLER_IMAGE_BASE = "https://cdn.brawlify.com/brawlers/borders"

_map_cache: dict[str, str] = {}
_last_fetch: float = 0
CACHE_TTL = 6 * 60 * 60  # 6 hours in seconds


async def load_map_data():
    global _map_cache, _last_fetch
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BRAWLAPI_MAPS_URL) as resp:
                if not resp.ok:
                    print(f"BrawlAPI maps returned {resp.status}, using cached data.")
                    return
                data = await resp.json()

        maps = data.get("list", [])
        _map_cache.clear()
        for m in maps:
            name = m.get("name")
            url = m.get("imageUrl")
            if name and url:
                _map_cache[name.lower()] = url

        _last_fetch = time.time()
        print(f"Cached {len(_map_cache)} map images from BrawlAPI.")
    except Exception as e:
        print(f"Failed to load map images from BrawlAPI: {e}")


def get_map_image(map_name: str | None) -> str | None:
    if not map_name:
        return None
    # Refresh cache if stale (fire-and-forget is not needed here since
    # the poller calls load_map_data on startup; this is a fallback)
    if time.time() - _last_fetch > CACHE_TTL:
        # Will be refreshed next polling cycle
        pass
    return _map_cache.get(map_name.lower())


def get_brawler_image(brawler_id: int | None) -> str | None:
    if not brawler_id:
        return None
    return f"{BRAWLER_IMAGE_BASE}/{brawler_id}.png"
