const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { getPlayerByName, getAllPlayerNames, getDb } = require('../../src/database');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('reset')
    .setDescription('Reset all battle history for a player')
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
    await interaction.deferReply({ ephemeral: true });

    if (interaction.user.id !== process.env.PIC_ADMIN_ID) {
      await interaction.editReply('❌ Only the bot owner can use this command.');
      return;
    }

    const name = interaction.options.getString('name');
    const player = getPlayerByName(name);

    if (!player) {
      await interaction.editReply(`❌ Player **${name}** not found.`);
      return;
    }

    const db = getDb();
    const battles = db.prepare('DELETE FROM battles WHERE player_tag = ?').run(player.tag);
    const sets = db.prepare('DELETE FROM sets WHERE player_tag = ?').run(player.tag);

    const embed = new EmbedBuilder()
      .setColor(0xed4245)
      .setTitle('🗑️ History Reset')
      .setDescription(`Cleared all data for **${player.name}**`)
      .addFields(
        { name: 'Battles Deleted', value: `${battles.changes}`, inline: true },
        { name: 'Sets Deleted', value: `${sets.changes}`, inline: true },
      );

    await interaction.editReply({ embeds: [embed] });
  },
};
