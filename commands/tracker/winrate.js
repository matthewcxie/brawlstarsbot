const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { getPlayerByName, getPlayerStats, getAllPlayerNames } = require('../../src/database');
const { formatWinRate, resultEmoji } = require('../../src/utils');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('winrate')
    .setDescription('Show ranked win/loss stats for a player')
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

    const stats = getPlayerStats(player.tag);

    if (stats.overall.total === 0) {
      await interaction.editReply(`📭 No ranked battles recorded for **${player.name}** yet.`);
      return;
    }

    const { overall, byBrawler } = stats;
    const wr = formatWinRate(overall.wins, overall.total);
    const starRate = formatWinRate(overall.star_player_count, overall.total);

    // Overall stats column (set-based)
    const overallLines = [
      `🏆 **Sets Won:** ${overall.wins}`,
      `💀 **Sets Lost:** ${overall.losses}`,
      `📊 **Win Rate:** ${wr}`,
      '',
      `⭐ **Star Player:** ${overall.star_player_count}/${overall.total} (${starRate})`,
    ];

    // Per-brawler column (top 15, set-based)
    const brawlerLines = byBrawler.slice(0, 15).map(b => {
      const bwr = formatWinRate(b.wins, b.total);
      const sp = b.star_player_count > 0 ? ` ⭐${b.star_player_count}` : '';
      return `**${b.brawler_name}**: ${b.wins}W-${b.losses}L (${bwr})${sp}`;
    });

    if (brawlerLines.length === 0) {
      brawlerLines.push('No brawler data yet.');
    }

    const embed = new EmbedBuilder()
      .setColor(0xffd700)
      .setTitle(`📈 ${player.name} — Ranked Stats`)
      .addFields(
        {
          name: '🎯 Overall Record',
          value: overallLines.join('\n'),
          inline: true,
        },
        {
          name: '🎮 Top Brawlers',
          value: brawlerLines.join('\n'),
          inline: true,
        },
      )
      .setFooter({ text: `${overall.total} sets tracked` });

    await interaction.editReply({ embeds: [embed] });
  },
};
