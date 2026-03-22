# BrawlStarsBot

A Discord bot that tracks Brawl Stars ranked matches in real time. It polls the Brawl Stars API every 60 seconds, automatically detects best-of-3 sets for Mythic+ players, tracks win/loss stats with per-brawler breakdowns, and posts live match result embeds to a Discord channel.

## Features

- **Ranked Match Tracking** — Polls the Brawl Stars API every 60 seconds for new ranked games
- **Best-of-3 Set Detection** — Automatically groups consecutive ranked games into bo3 sets for Mythic+ players
- **Win/Loss Stats** — Overall and per-brawler win rates with star player tracking, accessed via `/winrate`
- **Live Match Results** — Posts rich embeds to a dedicated channel with map images, team rosters, set scores, and star players
- **Password-Protected Admin** — The `/mythic` command requires a password to toggle tracking

## Prerequisites

- **Node.js 19+** (uses `crypto.randomUUID()`)
- **A Discord Bot** — Create one at the [Discord Developer Portal](https://discord.com/developers/applications)
- **A Brawl Stars API Key** — Get one from [developer.brawlstars.com](https://developer.brawlstars.com)

## Setup

### 1. Clone and install

```bash
git clone https://github.com/matthewcxie/brawlstarsbot.git
cd brawlstarsbot
npm install
```

### 2. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** and give it a name
3. Go to the **Bot** tab and click **Add Bot**
4. Copy the **Bot Token** (you'll need this for `.env`)
5. Go to **Installation** in the left sidebar
6. Under **Default Install Settings → Guild Install**, add scopes: `bot`, `applications.commands`
7. Add Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`
8. Copy the **Install Link** and open it in your browser to invite the bot to your server

### 3. Get a Brawl Stars API Key

1. Go to [developer.brawlstars.com](https://developer.brawlstars.com)
2. Create an account and log in
3. Create a new API key — **bind it to your machine's public IP address**
4. Copy the key

> **Note:** The Brawl Stars API key is IP-locked. If your IP changes, you'll need to generate a new key.

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token
CLIENT_ID=your_discord_application_id
GUILD_ID=your_discord_server_id

# Brawl Stars API
BRAWL_API_KEY=your_brawl_stars_api_key

# Bot Settings
RESULTS_CHANNEL_ID=channel_id_for_match_results
MYTHIC_PASSWORD=choose_any_admin_password
```

**How to get Discord IDs:**
- Enable **Developer Mode** in Discord (Settings → Advanced → Developer Mode)
- **Guild ID:** Right-click your server name → Copy Server ID
- **Channel ID:** Right-click the results channel → Copy Channel ID
- **Client ID:** Discord Developer Portal → General Information → Application ID

### 5. Deploy slash commands

```bash
npm run deploy
```

This registers `/add`, `/mythic`, and `/winrate` as slash commands in your server. Run this once, and again any time you change command definitions.

### 6. Start the bot

```bash
npm start
```

You should see:
```
Database initialized.
✅ Logged in as YourBot#1234
Cached 852 map images from BrawlAPI.
🔄 Starting ranked match polling (every 60s)...
```

## Commands

| Command | Description |
|---------|-------------|
| `/add <player_tag>` | Add a Brawl Stars player to the tracker (e.g. `/add #2YQ8V09CL`) |
| `/mythic <player_name> <password>` | Toggle best-of-3 ranked tracking for a player (password required) |
| `/winrate <name>` | Show win/loss stats with overall record, set record, star player rate, and per-brawler breakdown |

## How It Works

1. **Add players** with `/add` — validates the tag against the Brawl Stars API and stores them
2. **Enable tracking** with `/mythic` — activates polling for that player's ranked games in best-of-3 mode
3. **Automatic detection** — every 60 seconds, the bot fetches battle logs and groups new ranked games into bo3 sets
4. **Live posting** — when a set completes, a rich embed is posted to your results channel with map image, team rosters, per-game results, and star players
5. **Stats tracking** — use `/winrate` to see overall and per-brawler win rates with star player stats

### Best-of-3 Set Detection

The Brawl Stars API reports individual games, not sets. The bot infers bo3 sets by grouping consecutive ranked battles that occur within 5 minutes of each other. A set completes when one side reaches 2 wins. Sets left open for more than 30 minutes are auto-closed.

You can tune these constants in `src/poller.js`:
- `SET_TIME_GAP_MINUTES` (default: 5) — max gap between games in the same set
- `STALE_SET_MINUTES` (default: 30) — auto-close incomplete sets after this long

## Project Structure

```
brawlstarsbot/
├── index.js                  # Bot entry point
├── deploy-commands.js        # Slash command registration script
├── src/
│   ├── database.js           # SQLite schema and query helpers
│   ├── api.js                # Brawl Stars API wrapper
│   ├── poller.js             # Polling loop and bo3 set detection
│   ├── mapImages.js          # Map image caching from BrawlAPI
│   ├── embeds.js             # Discord embed builders
│   └── utils.js              # Tag normalization, time helpers, emojis
├── commands/tracker/         # Slash command handlers
├── events/                   # Discord event handlers
└── data/                     # SQLite database (auto-created, gitignored)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Missing Access` on deploy | Bot hasn't been invited with `applications.commands` scope — re-invite using the install link |
| `403` from Brawl Stars API | API key is IP-locked — regenerate it at developer.brawlstars.com with your current IP |
| No matches appearing | Battle logs can take up to 30 minutes to update in the API; also ensure the player is toggled to mythic mode |
| Sets splitting incorrectly | Adjust `SET_TIME_GAP_MINUTES` in `src/poller.js` (increase if games are being split across sets) |

## License

MIT
