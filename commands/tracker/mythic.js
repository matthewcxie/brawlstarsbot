const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { getPlayerByName, toggleMythic, getAllPlayerNames } = require('../../src/database');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('mythic')
    .setDescription('Toggle mythic (best-of-3) tracking for a player')
    .addStringOption(option =>
      option
        .setName('player_name')
        .setDescription('The player\'s in-game name')
        .setRequired(true)
        .setAutocomplete(true),
    )
    .addStringOption(option =>
      option
        .setName('password')
        .setDescription('Admin password')
        .setRequired(true),
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
    // Always ephemeral so the password isn't visible
    await interaction.deferReply({ ephemeral: true });

    const password = interaction.options.getString('password');

    if (password !== process.env.MYTHIC_PASSWORD) {
      await interaction.editReply('❌ Incorrect password.');
      return;
    }

    const name = interaction.options.getString('player_name');
    const player = getPlayerByName(name);

    if (!player) {
      await interaction.editReply(
        `❌ Player **${name}** not found. Add them first with \`/add\`.`,
      );
      return;
    }

    const newValue = toggleMythic(player.tag);
    const status = newValue ? 'enabled' : 'disabled';
    const emoji = newValue ? '🟢' : '🔴';

    const embed = new EmbedBuilder()
      .setColor(newValue ? 0x57f287 : 0xed4245)
      .setTitle(`${emoji} Mythic Mode ${status.charAt(0).toUpperCase() + status.slice(1)}`)
      .setDescription(
        newValue
          ? `**${player.name}** is now being tracked in **best-of-3** ranked mode.`
          : `**${player.name}** has been removed from active ranked tracking.`,
      );

    await interaction.editReply({ embeds: [embed] });
  },
};
