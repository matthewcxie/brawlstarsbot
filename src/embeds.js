const { EmbedBuilder } = require('discord.js');
const { getMapImage, getBrawlerImage } = require('./mapImages');
const { resultEmoji, modeEmoji, formatModeName } = require('./utils');

/**
 * Build an embed for a completed best-of-3 set.
 */
function buildSetEmbed(set, battles, playerTag) {
  const isVictory = set.result === 'victory';
  const color = isVictory ? 0x57f287 : 0xed4245;
  const resultText = isVictory ? 'VICTORY' : 'DEFEAT';

  // Use the first battle's map info for the embed
  const firstBattle = battles[0];
  const mapName = firstBattle?.map || 'Unknown Map';
  const mode = firstBattle?.mode || 'unknown';
  const mapImage = getMapImage(mapName);

  const embed = new EmbedBuilder()
    .setColor(color)
    .setTitle(`${isVictory ? '🏆' : '💀'} Ranked Set — ${resultText}`)
    .setDescription(`${modeEmoji(mode)} **${formatModeName(mode)}** on **${mapName}**\n\n📊 **Set Score: ${set.wins} - ${set.losses}**`);

  // Map image as the large header image
  if (mapImage) {
    embed.setImage(mapImage);
    embed.setAuthor({ name: mapName, iconURL: mapImage });
  }

  // Individual game results with brawlers played
  for (const battle of battles) {
    const gameResult = battle.result === 'victory' ? '✅ Win' : '❌ Loss';
    const starText = battle.is_star_player ? ' ⭐' : '';
    const duration = battle.duration ? `${Math.floor(battle.duration / 60)}:${String(battle.duration % 60).padStart(2, '0')}` : '?:??';

    // Get all brawlers played in this game
    const brawlerLines = getBrawlerSummary(battle);

    embed.addFields({
      name: `Game ${battle.set_game_number} — ${gameResult}${starText}`,
      value: `🎮 ${battle.brawler_name || 'Unknown'} • ⏱️ ${duration}\n${brawlerLines}`,
      inline: false,
    });
  }

  // Team rosters with brawlers from the most recent game
  const lastBattle = battles[battles.length - 1];
  const teamsData = parseTeamsWithBrawlers(lastBattle);
  if (teamsData) {
    embed.addFields(
      { name: '\u200b', value: '\u200b', inline: false },
      { name: '🔵 Your Team', value: teamsData.team1Lines.join('\n'), inline: true },
      { name: '🔴 Opponent', value: teamsData.team2Lines.join('\n'), inline: true },
    );
  }

  // Brawler icon as thumbnail (tracked player's brawler from first game)
  if (firstBattle?.brawler_id) {
    const brawlerImg = getBrawlerImage(firstBattle.brawler_id);
    if (brawlerImg) {
      embed.setThumbnail(brawlerImg);
    }
  }

  embed.setTimestamp(new Date());
  return embed;
}

/**
 * Build an embed for a single ranked game.
 */
function buildGameEmbed(battle) {
  const isVictory = battle.result === 'victory';
  const color = isVictory ? 0x57f287 : 0xed4245;
  const mapImage = getMapImage(battle.map);

  const embed = new EmbedBuilder()
    .setColor(color)
    .setTitle(`${resultEmoji(battle.result)} Ranked Game — ${battle.map || 'Unknown'}`)
    .setDescription(`${modeEmoji(battle.mode)} **${formatModeName(battle.mode)}**`);

  if (mapImage) {
    embed.setImage(mapImage);
  }

  if (battle.brawler_id) {
    embed.setThumbnail(getBrawlerImage(battle.brawler_id));
  }

  const starText = battle.is_star_player ? ' ⭐' : '';
  embed.addFields(
    { name: 'Result', value: `${isVictory ? '✅ Win' : '❌ Loss'}${starText}`, inline: true },
    { name: 'Brawler', value: battle.brawler_name || 'Unknown', inline: true },
  );

  const teamsData = parseTeamsWithBrawlers(battle);
  if (teamsData) {
    embed.addFields(
      { name: '🔵 Your Team', value: teamsData.team1Lines.join('\n'), inline: true },
      { name: '🔴 Opponent', value: teamsData.team2Lines.join('\n'), inline: true },
    );
  }

  embed.setTimestamp(new Date());
  return embed;
}

// ── Helpers ──

function safeParse(json) {
  try {
    return JSON.parse(json);
  } catch {
    return null;
  }
}

/**
 * Get a compact summary of brawlers from both teams for a game.
 */
function getBrawlerSummary(battle) {
  const teams = safeParse(battle.teams_json);
  if (!teams || teams.length < 2) return '';

  let playerTeamIndex = 0;
  for (let i = 0; i < teams.length; i++) {
    for (const p of teams[i]) {
      if (p.tag === battle.player_tag) {
        playerTeamIndex = i;
      }
    }
  }
  const opponentTeamIndex = playerTeamIndex === 0 ? 1 : 0;

  const teamBrawlers = teams[playerTeamIndex].map(p => p.brawler?.name || '?').join(', ');
  const oppBrawlers = teams[opponentTeamIndex].map(p => p.brawler?.name || '?').join(', ');

  return `🔵 ${teamBrawlers}\n🔴 ${oppBrawlers}`;
}

/**
 * Parse teams with brawler names and icons for display.
 */
function parseTeamsWithBrawlers(battle) {
  const teams = safeParse(battle.teams_json);
  if (!teams || teams.length < 2) return null;

  let playerTeamIndex = 0;
  for (let i = 0; i < teams.length; i++) {
    for (const p of teams[i]) {
      if (p.tag === battle.player_tag) {
        playerTeamIndex = i;
      }
    }
  }

  const opponentTeamIndex = playerTeamIndex === 0 ? 1 : 0;

  const formatPlayer = (p, isTracked) => {
    const name = isTracked ? `**${p.name}**` : p.name;
    const brawler = p.brawler?.name || '?';
    return `${name}\n└ ${brawler}`;
  };

  const team1Lines = teams[playerTeamIndex].map(p =>
    formatPlayer(p, p.tag === battle.player_tag),
  );
  const team2Lines = teams[opponentTeamIndex].map(p =>
    formatPlayer(p, false),
  );

  return { team1Lines, team2Lines };
}

module.exports = { buildSetEmbed, buildGameEmbed };
