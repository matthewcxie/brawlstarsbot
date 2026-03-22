const { Events } = require('discord.js');
const { startPolling } = require('../src/poller');
const { loadMapData } = require('../src/mapImages');

module.exports = {
  name: Events.ClientReady,
  once: true,
  async execute(client) {
    console.log(`✅ Logged in as ${client.user.tag}`);

    // Cache map images from BrawlAPI
    await loadMapData();

    // Start 60-second polling loop
    console.log('🔄 Starting ranked match polling (every 60s)...');
    startPolling(client);
    setInterval(() => startPolling(client), 60_000);
  },
};
