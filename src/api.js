const BASE_URL = 'https://api.brawlstars.com/v1';

function encodeTag(tag) {
  return encodeURIComponent(tag);
}

async function apiFetch(endpoint) {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    headers: { Authorization: `Bearer ${process.env.BRAWL_API_KEY}` },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    const error = new Error(`Brawl Stars API ${res.status}: ${res.statusText}`);
    error.status = res.status;
    error.body = body;
    throw error;
  }

  return res.json();
}

async function getPlayer(tag) {
  return apiFetch(`/players/${encodeTag(tag)}`);
}

async function getBattleLog(tag) {
  const data = await apiFetch(`/players/${encodeTag(tag)}/battlelog`);
  return data.items || [];
}

async function getBrawlers() {
  const data = await apiFetch('/brawlers');
  return data.items || [];
}

module.exports = { getPlayer, getBattleLog, getBrawlers };
