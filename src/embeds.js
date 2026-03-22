const { EmbedBuilder } = require('discord.js');
const { getMapImage } = require('./mapImages');
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
    .setDescription(`${modeEmoji(mode)} **${formatModeName(mode)}** on **${mapName}**`);

  if (mapImage) {
    embed.setThumbnail(mapImage);
  }

  // Set score
  embed.addFields({
    name: '📊 Set Score',
    value: `**${set.wins}** - **${set.losses}**`,
    inline: false,
  });

  // Individual game results
  for (const battle of battles) {
    const gameResult = battle.result === 'victory' ? '✅ Win' : '❌ Loss';
    const starText = battle.is_star_player ? ' ⭐' : '';
    const duration = battle.duration ? `${Math.floor(battle.duration / 60)}:${String(battle.duration % 60).padStart(2, '0')}` : '?:??';

    embed.addFields({
      name: `Game ${battle.set_game_number}`,
      value: `${gameResult}${starText}\n🎮 ${battle.brawler_name || 'Unknown'}\n⏱️ ${duration}`,
      inline: true,
    });
  }

  // Team rosters from the first battle (teams are the same across a set)
  const teamsData = parseTeams(firstBattle);
  if (teamsData) {
    const { team1Lines, team2Lines } = teamsData;
    embed.addFields(
      { name: '\u200b', value: '\u200b', inline: false }, // spacer
      { name: '🔵 Team', value: team1Lines.join('\n'), inline: true },
      { name: '🔴 Opponent', value: team2Lines.join('\n'), inline: true },
    );
  }

  // Star player from each game
  const starPlayers = battles
    .map(b => {
      const teams = safeParse(b.teams_json);
      if (!teams) return null;
      // Find star player in teams data
      for (const team of teams) {
        for (const p of team) {
          if (p.tag === getStarPlayerTag(b)) {
            return `Game ${b.set_game_number}: **${p.name}** (${p.brawler?.name || '?'})`;
          }
        }
      }
      return null;
    })
    .filter(Boolean);

  if (starPlayers.length > 0) {
    embed.addFields({
      name: '⭐ Star Players',
      value: starPlayers.join('\n'),
      inline: false,
    });
  }

  embed.setTimestamp(new Date());
  return embed;
}

/**
 * Build an embed for a single ranked game (used as fallback).
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
    embed.setThumbnail(mapImage);
  }

  const starText = battle.is_star_player ? ' ⭐' : '';
  embed.addFields(
    { name: 'Result', value: `${isVictory ? '✅ Win' : '❌ Loss'}${starText}`, inline: true },
    { name: 'Brawler', value: battle.brawler_name || 'Unknown', inline: true },
  );

  const teamsData = parseTeams(battle);
  if (teamsData) {
    embed.addFields(
      { name: '🔵 Team', value: teamsData.team1Lines.join('\n'), inline: true },
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

function parseTeams(battle) {
  const teams = safeParse(battle.teams_json);
  if (!teams || teams.length < 2) return null;

  // Determine which team the tracked player is on
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
    return `${name} (${p.brawler?.name || '?'})`;
  };

  const team1Lines = teams[playerTeamIndex].map(p =>
    formatPlayer(p, p.tag === battle.player_tag),
  );
  const team2Lines = teams[opponentTeamIndex].map(p =>
    formatPlayer(p, false),
  );

  return { team1Lines, team2Lines };
}

function getStarPlayerTag(battle) {
  const teams = safeParse(battle.teams_json);
  if (!teams) return null;
  // The star player info is stored in the raw API data within teams_json
  // We check if the tracked player was star player via is_star_player flag
  // For display, we'd need the original starPlayer field — stored separately would be ideal
  // For now, if is_star_player is set, return the player_tag
  if (battle.is_star_player) return battle.player_tag;
  return null;
}

module.exports = { buildSetEmbed, buildGameEmbed };
