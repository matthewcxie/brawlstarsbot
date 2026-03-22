const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const {
  getPlayerByName, getAllPlayerNames, getAllBattlesForPlayer, getDb,
} = require('../../src/database');
const { formatWinRate } = require('../../src/utils');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('carry')
    .setDescription('Show win rates with each tracked teammate')
    .addStringOption(option =>
      option
        .setName('name')
        .setDescription('The player\'s in-game name')
        .setRequired(true)
        .setAutocomplete(true),
    ),

  async autocomplete(interaction) {
    const focused = interaction.options.getFocused().toLowerCase();
    const names = getAllPlayerNames();
    const filtered = names
      .filter(n => n.toLowerCase().includes(focused))
      .slice(0, 25);
    await interaction.respond(filtered.map(name => ({ name, value: name })));
  },

  async execute(interaction) {
    await interaction.deferReply();

    const name = interaction.options.getString('name');
    const player = getPlayerByName(name);

    if (!player) {
      await interaction.editReply(`❌ Player **${name}** not found.`);
      return;
    }

    // Get all tracked player tags for comparison
    const db = getDb();
    const allPlayers = db.prepare('SELECT tag, name FROM players').all();
    const trackedTags = new Map(allPlayers.map(p => [p.tag, p.name]));

    // Get all battles for this player
    const battles = getAllBattlesForPlayer(player.tag);

    if (battles.length === 0) {
      await interaction.editReply(`📭 No ranked battles recorded for **${player.name}** yet.`);
      return;
    }

    // For each battle, find which tracked players were on the same team
    const teammateStats = new Map(); // tag -> { name, wins, losses }

    for (const battle of battles) {
      let teams;
      try {
        teams = JSON.parse(battle.teams_json);
      } catch {
        continue;
      }
      if (!teams || teams.length < 2) continue;

      // Find which team the player is on
      let playerTeam = null;
      for (const team of teams) {
        for (const p of team) {
          if (p.tag === player.tag) {
            playerTeam = team;
            break;
          }
        }
        if (playerTeam) break;
      }
      if (!playerTeam) continue;

      // Check each teammate against tracked players
      for (const teammate of playerTeam) {
        if (teammate.tag === player.tag) continue; // skip self
        if (!trackedTags.has(teammate.tag)) continue; // skip non-tracked

        if (!teammateStats.has(teammate.tag)) {
          teammateStats.set(teammate.tag, {
            name: trackedTags.get(teammate.tag),
            wins: 0,
            losses: 0,
          });
        }

        const stats = teammateStats.get(teammate.tag);
        if (battle.result === 'victory') {
          stats.wins++;
        } else if (battle.result === 'defeat') {
          stats.losses++;
        }
      }
    }

    if (teammateStats.size === 0) {
      await interaction.editReply(`📭 **${player.name}** hasn't played with any other tracked players yet.`);
      return;
    }

    // Sort by win rate descending
    const sorted = [...teammateStats.values()]
      .map(s => ({
        ...s,
        total: s.wins + s.losses,
        winRate: s.wins + s.losses > 0 ? s.wins / (s.wins + s.losses) : 0,
      }))
      .sort((a, b) => b.winRate - a.winRate);

    // Build the embed
    const lines = sorted.map((s, i) => {
      const wr = formatWinRate(s.wins, s.total);
      const bar = getWinRateBar(s.winRate);
      const medal = i === 0 ? '👑' : i === sorted.length - 1 && sorted.length > 1 ? '💀' : '•';
      return `${medal} **${s.name}** — ${s.wins}W ${s.losses}L (${wr})\n  ${bar}  ${s.total} games`;
    });

    const embed = new EmbedBuilder()
      .setColor(0x00c8ff)
      .setTitle(`🤝 ${player.name} — Teammate Win Rates`)
      .setDescription(lines.join('\n\n'))
      .setFooter({ text: `Based on ${battles.length} tracked games` });

    await interaction.editReply({ embeds: [embed] });
  },
};

function getWinRateBar(rate) {
  const filled = Math.round(rate * 10);
  const empty = 10 - filled;
  return '🟩'.repeat(filled) + '⬛'.repeat(empty);
}
