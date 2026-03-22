const { Events } = require('discord.js');
const { startPolling } = require('../src/poller');
const { loadMapData } = require('../src/mapImages');
const { checkAndPostDailyPic } = require('../src/dailyPic');

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

    // Start daily pic scheduler (checks every 60s, posts at midnight EST)
    console.log('🖼️ Starting daily pic scheduler...');
    checkAndPostDailyPic(client);
    setInterval(() => checkAndPostDailyPic(client), 60_000);
  },
};
