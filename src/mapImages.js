const BRAWLAPI_MAPS_URL = 'https://api.brawlapi.com/v1/maps';

let mapCache = new Map();
let lastFetch = 0;
const CACHE_TTL = 6 * 60 * 60 * 1000; // 6 hours

async function loadMapData() {
  try {
    const res = await fetch(BRAWLAPI_MAPS_URL);
    if (!res.ok) {
      console.warn(`BrawlAPI maps returned ${res.status}, using cached data.`);
      return;
    }
    const data = await res.json();
    const maps = data.list || [];
    mapCache.clear();
    for (const m of maps) {
      if (m.name && m.imageUrl) {
        mapCache.set(m.name.toLowerCase(), m.imageUrl);
      }
    }
    lastFetch = Date.now();
    console.log(`Cached ${mapCache.size} map images from BrawlAPI.`);
  } catch (error) {
    console.warn('Failed to load map images from BrawlAPI:', error.message);
  }
}

function getMapImage(mapName) {
  if (!mapName) return null;

  // Refresh cache if stale
  if (Date.now() - lastFetch > CACHE_TTL) {
    loadMapData().catch(() => {});
  }

  return mapCache.get(mapName.toLowerCase()) || null;
}

module.exports = { loadMapData, getMapImage };
