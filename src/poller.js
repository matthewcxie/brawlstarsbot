const crypto = require('node:crypto');
const { getBattleLog } = require('./api');
const {
  getAllMythicPlayers,
  insertBattle,
  getUnassignedBattles,
  assignBattleToSet,
  createSet,
  getIncompleteSet,
  updateSetScore,
  getUnpostedCompletedSets,
  markSetPosted,
  getSetBattles,
  markBattlesPosted,
  getStaleSets,
  forceCompleteSet,
} = require('./database');
const { timeDiffMinutes } = require('./utils');
const { buildSetEmbed } = require('./embeds');

const SET_TIME_GAP_MINUTES = 5;
const STALE_SET_MINUTES = 30;

let isPolling = false;

async function startPolling(client) {
  // Prevent overlapping poll cycles
  if (isPolling) return;
  isPolling = true;

  try {
    const players = getAllMythicPlayers();
    if (players.length === 0) return;

    for (const player of players) {
      try {
        await processPlayer(player, client);
      } catch (error) {
        if (error.status === 429) {
          console.warn(`Rate limited by Brawl Stars API. Skipping remaining players this cycle.`);
          break;
        }
        console.error(`Error processing ${player.name} (${player.tag}):`, error.message);
      }
    }

    // Post any completed sets that haven't been posted yet
    await postCompletedSets(client);

    // Close stale incomplete sets
    closeStalesSets();
  } finally {
    isPolling = false;
  }
}

async function processPlayer(player, client) {
  // 1. Fetch battle log
  const battles = await getBattleLog(player.tag);

  // 2. Filter to ranked battles (soloRanked and ranked/teamRanked)
  const rankedTypes = new Set(['soloRanked', 'teamRanked', 'ranked']);
  const rankedBattles = battles.filter(b =>
    b.battle && rankedTypes.has(b.battle.type),
  );

  if (rankedBattles.length === 0) return;

  // 3. Insert new battles (newest first in API, but we process oldest first)
  let newCount = 0;
  for (const raw of rankedBattles) {
    const battle = extractBattleData(raw, player.tag);
    if (!battle) continue;

    const result = insertBattle(battle);
    if (result.changes > 0) newCount++;
  }

  if (newCount > 0) {
    console.log(`📥 ${player.name}: ${newCount} new ranked battle(s) found.`);
  }

  // 4. Group unassigned battles into bo3 sets
  groupBattlesIntoSets(player.tag);
}

/**
 * Extract relevant battle data from the raw API response.
 */
function extractBattleData(raw, playerTag) {
  const battle = raw.battle;
  const event = raw.event;
  if (!battle || !event) return null;

  // Find the tracked player in the teams to get their brawler
  let playerBrawler = null;
  let isStarPlayer = false;

  if (battle.teams) {
    for (const team of battle.teams) {
      for (const p of team) {
        if (p.tag === playerTag) {
          playerBrawler = p.brawler;
        }
      }
    }
  }

  // Check star player
  if (battle.starPlayer && battle.starPlayer.tag === playerTag) {
    isStarPlayer = true;
  }

  return {
    player_tag: playerTag,
    battle_time: raw.battleTime,
    battle_type: battle.type,
    mode: event.mode || battle.mode,
    map: event.map,
    result: battle.result,
    is_star_player: isStarPlayer,
    brawler_name: playerBrawler?.name || null,
    brawler_id: playerBrawler?.id || null,
    duration: battle.duration || null,
    teams_json: battle.teams ? JSON.stringify(battle.teams) : null,
  };
}

/**
 * Group unassigned battles into sets.
 *
 * - ranked (team ranked): bo3 — group consecutive games within 5 min
 * - soloRanked: bo1 — each game is its own completed set
 */
function groupBattlesIntoSets(playerTag) {
  const unassigned = getUnassignedBattles(playerTag);
  if (unassigned.length === 0) return;

  for (const battle of unassigned) {
    // soloRanked = best of 1, each game is its own set
    if (battle.battle_type === 'soloRanked') {
      const setId = crypto.randomUUID();
      createSet(setId, playerTag, battle.battle_time);
      assignBattleToSet(battle.id, setId, 1);
      const wins = battle.result === 'victory' ? 1 : 0;
      const losses = battle.result === 'defeat' ? 1 : 0;
      updateSetScore(setId, wins, losses);
      // Force complete immediately since bo1
      forceCompleteSet(setId);
      continue;
    }

    // ranked (team ranked) = best of 3
    let activeSet = getIncompleteSet(playerTag);

    if (activeSet) {
      const setBattles = getSetBattles(activeSet.id);
      const lastBattle = setBattles[setBattles.length - 1];

      if (lastBattle && timeDiffMinutes(lastBattle.battle_time, battle.battle_time) <= SET_TIME_GAP_MINUTES) {
        const gameNumber = setBattles.length + 1;
        assignBattleToSet(battle.id, activeSet.id, gameNumber);

        const newWins = activeSet.wins + (battle.result === 'victory' ? 1 : 0);
        const newLosses = activeSet.losses + (battle.result === 'defeat' ? 1 : 0);
        updateSetScore(activeSet.id, newWins, newLosses);
        continue;
      }
    }

    // Create a new set
    const setId = crypto.randomUUID();
    createSet(setId, playerTag, battle.battle_time);
    assignBattleToSet(battle.id, setId, 1);

    const wins = battle.result === 'victory' ? 1 : 0;
    const losses = battle.result === 'defeat' ? 1 : 0;
    updateSetScore(setId, wins, losses);
  }
}

/**
 * Post embeds for all completed but unposted sets.
 */
async function postCompletedSets(client) {
  const channelIds = (process.env.RESULTS_CHANNEL_IDS || process.env.RESULTS_CHANNEL_ID || '')
    .split(',')
    .map(id => id.trim())
    .filter(Boolean);

  if (channelIds.length === 0) return;

  // Resolve all channels
  const channels = [];
  for (const id of channelIds) {
    const channel = client.channels.cache.get(id)
      || await client.channels.fetch(id).catch(() => null);
    if (channel) {
      channels.push(channel);
    } else {
      console.warn(`Results channel ${id} not found.`);
    }
  }

  if (channels.length === 0) return;

  const unposted = getUnpostedCompletedSets();

  for (const set of unposted) {
    try {
      const battles = getSetBattles(set.id);

      // Determine if this is a valid completed set:
      // - soloRanked: 1 game is valid (bo1)
      // - ranked: need at least 2 games with a 2-win result (bo3)
      const isSoloRanked = battles.length === 1 && battles[0].battle_type === 'soloRanked';
      const isValidBo3 = battles.length >= 2 && (set.wins >= 2 || set.losses >= 2);

      if (!isSoloRanked && !isValidBo3) {
        markSetPosted(set.id); // Skip incomplete/invalid sets
        continue;
      }

      const embed = buildSetEmbed(set, battles, set.player_tag);

      // Post to all results channels
      for (const channel of channels) {
        await channel.send({ embeds: [embed] }).catch(err =>
          console.error(`Failed to post to ${channel.id}:`, err.message),
        );
      }

      markSetPosted(set.id);
      markBattlesPosted(set.id);
      console.log(`📤 Posted set result for ${set.player_tag}: ${set.result} (${set.wins}-${set.losses})`);
    } catch (error) {
      console.error(`Failed to post set ${set.id}:`, error.message);
    }
  }
}

/**
 * Close sets that have been open for too long (player quit mid-set).
 * Sets with fewer than 2 games are silently discarded — they were
 * likely the first game of a bo3 that never continued.
 */
function closeStalesSets() {
  const stale = getStaleSets(STALE_SET_MINUTES);
  for (const set of stale) {
    const battles = getSetBattles(set.id);
    if (battles.length < 2) {
      // Not a real set — silently close without posting
      forceCompleteSet(set.id);
      markSetPosted(set.id);
    } else {
      forceCompleteSet(set.id);
      console.log(`⏰ Auto-closed stale set ${set.id} for ${set.player_tag} (${set.wins}-${set.losses})`);
    }
  }
}

module.exports = { startPolling };
