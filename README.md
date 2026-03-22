# BrawlBotAdvanced

A Discord bot that tracks Brawl Stars ranked matches. It polls the Brawl Stars API every 60 seconds, detects best-of-3 sets for Mythic+ players, tracks win/loss stats with per-brawler breakdowns, and posts live match results to a Discord channel.

## Features

- **Ranked Match Tracking** — Polls the Brawl Stars API every 60 seconds for new ranked games
- **Best-of-3 Set Detection** — Automatically groups consecutive ranked games into bo3 sets for Mythic+ players
- **Win/Loss Stats** — Overall and per-brawler win rates with star player tracking
- **Live Match Results** — Posts rich embeds to a dedicated channel with map images, team rosters, scores, and star players
- **Password-Protected Admin** — The `/mythic` command requires a password to toggle tracking

## Prerequisites

- **Node.js 19+** (uses `crypto.randomUUID()`)
- **Discord Bot** — Create one at the [Discord Developer Portal](https://discord.com/developers/applications)
- **Brawl Stars API Key** — Get one from [developer.brawlstars.com](https://developer.brawlstars.com)

## Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/brawlbotadvanced.git
cd brawlbotadvanced
npm install
```

### 2. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and name it
3. Go to **Bot** tab → click "Add Bot"
4. Copy the **Bot Token**
5. Under "Privileged Gateway Intents", enable what you need (none are strictly required for this bot)
6. Go to **OAuth2 → URL Generator**
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`
7. Copy the generated URL and open it to invite the bot to your server

### 3. Get a Brawl Stars API Key

1. Go to [developer.brawlstars.com](https://developer.brawlstars.com)
2. Create an account and log in
3. Create a new API key — **bind it to your server's IP address**
4. Copy the key

### 4. Configure environment variables

Copy `.env` and fill in your values:

```env
DISCORD_TOKEN=your_discord_bot_token
CLIENT_ID=your_discord_application_id
GUILD_ID=your_discord_server_id
BRAWL_API_KEY=your_brawl_stars_api_key
RESULTS_CHANNEL_ID=channel_id_for_match_results
MYTHIC_PASSWORD=choose_any_admin_password
```

**How to get IDs:**
- Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
- Right-click your server → "Copy Server ID" → `GUILD_ID`
- Right-click the results channel → "Copy Channel ID" → `RESULTS_CHANNEL_ID`
- Application ID is on the Discord Developer Portal → General Information

### 5. Deploy slash commands

```bash
npm run deploy
```

This registers `/add`, `/mythic`, and `/winrate` in your Discord server. You only need to run this once (or when you modify command definitions).

### 6. Start the bot

```bash
npm start
```

## Commands

| Command | Description |
|---------|-------------|
| `/add <player_tag>` | Add a Brawl Stars player to the tracker. Tag format: `#2YQ8V09CL` |
| `/mythic <player_name> <password>` | Toggle best-of-3 ranked tracking for a player (password required) |
| `/winrate <name>` | Show ranked win/loss stats with overall and per-brawler breakdowns |

## How It Works

1. **Add players** with `/add` — validates the tag against the Brawl Stars API
2. **Enable tracking** with `/mythic` — starts polling that player's battle log every 60 seconds
3. **Automatic detection** — when new ranked games appear, the bot groups them into best-of-3 sets
4. **Live posting** — completed sets are posted as rich embeds to your results channel
5. **Stats tracking** — use `/winrate` to see overall and per-brawler stats with star player rates

### Best-of-3 Detection

The bot groups consecutive ranked battles into sets by checking timestamp proximity. Games within 5 minutes of each other are considered part of the same set. A set is complete when one side reaches 2 wins. Sets open for more than 30 minutes without new games are auto-closed.

## Project Structure

```
brawlbotadvanced/
├── index.js                  # Bot entry point
├── deploy-commands.js        # Slash command registration
├── src/
│   ├── database.js           # SQLite schema and queries
│   ├── api.js                # Brawl Stars API wrapper
│   ├── poller.js             # Polling loop and bo3 detection
│   ├── mapImages.js          # Map image caching from BrawlAPI
│   ├── embeds.js             # Discord embed builders
│   └── utils.js              # Tag normalization, time helpers
├── commands/tracker/         # Slash command handlers
├── events/                   # Discord event handlers
└── data/                     # SQLite database (auto-created)
```

## License

MIT
