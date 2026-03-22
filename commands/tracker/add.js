const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { getPlayer } = require('../../src/api');
const { addPlayer } = require('../../src/database');
const { normalizeTag } = require('../../src/utils');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('add')
    .setDescription('Add a Brawl Stars player to the tracker')
    .addStringOption(option =>
      option
        .setName('player_tag')
        .setDescription('The player tag (e.g. #2YQ8V09CL)')
        .setRequired(true),
    ),

  async execute(interaction) {
    await interaction.deferReply();

    const rawTag = interaction.options.getString('player_tag');
    const tag = normalizeTag(rawTag);

    try {
      const player = await getPlayer(tag);

      addPlayer(tag, player.name);

      const embed = new EmbedBuilder()
        .setColor(0x00c8ff)
        .setTitle('✅ Player Added')
        .setDescription(`**${player.name}** has been added to the tracker.`)
        .addFields(
          { name: '🏷️ Tag', value: tag, inline: true },
          { name: '🏆 Trophies', value: player.trophies.toString(), inline: true },
          { name: '📊 Highest', value: player.highestTrophies.toString(), inline: true },
        )
        .setFooter({ text: 'Use /mythic to enable ranked tracking' });

      await interaction.editReply({ embeds: [embed] });
    } catch (error) {
      if (error.status === 404) {
        await interaction.editReply(`❌ Player with tag \`${tag}\` not found. Double-check the tag.`);
      } else {
        console.error('Error adding player:', error);
        await interaction.editReply('❌ Failed to fetch player data from Brawl Stars API.');
      }
    }
  },
};
