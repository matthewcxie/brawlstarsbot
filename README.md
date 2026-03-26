# BrawlStarsBot

A Discord bot that tracks Brawl Stars ranked matches in real time. It polls the Brawl Stars API every 60 seconds, automatically detects best-of-3 sets for Mythic+ players, tracks win/loss stats with per-brawler breakdowns, and posts live match result embeds to Discord channels.

## Features

- **Ranked Match Tracking** — Polls the Brawl Stars API every 60 seconds for new soloRanked games
- **Best-of-3 Set Detection** — Automatically groups consecutive ranked games into bo3 sets for Mythic+ players
- **Win/Loss Stats** — Overall and per-brawler win rates with star player tracking
- **Teammate Analysis** — See win rates when playing with each tracked teammate
- **Live Match Results** — Posts rich embeds with map images, team rosters, set scores, and star players
- **Multi-Channel Support** — Post results to multiple Discord channels simultaneously

## Prerequisites

- **Python 3.11+**
- **A Discord Bot** — Create one at the [Discord Developer Portal](https://discord.com/developers/applications)
- **A Brawl Stars API Key** — Get one from [developer.brawlstars.com](https://developer.brawlstars.com)

## Setup

### 1. Clone and install

```bash
git clone https://github.com/matthewcxie/brawlstarsbot.git
cd brawlstarsbot/brawlbot-py
pip install -r requirements.txt
```

### 2. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** and give it a name
3. Go to the **Bot** tab and click **Add Bot**
4. Copy the **Bot Token** (you'll need this for `.env`)
5. Go to **Installation** in the left sidebar
6. Under **Default Install Settings > Guild Install**, add scopes: `bot`, `applications.commands`
7. Add Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`
8. Copy the **Install Link** and open it in your browser to invite the bot to your server

### 3. Get a Brawl Stars API Key

1. Go to [developer.brawlstars.com](https://developer.brawlstars.com)
2. Create an account and log in
3. Create a new API key — **bind it to your machine's public IP address**
4. Copy the key

> **Note:** The Brawl Stars API key is IP-locked. If your IP changes, you'll need to generate a new key.

### 4. Configure environment variables

Create a `.env` file in the `brawlbot-py/` directory:

```env
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token
CLIENT_ID=your_discord_application_id
GUILD_ID=your_discord_server_id

# Brawl Stars API
BRAWL_API_KEY=your_brawl_stars_api_key

# Bot Settings
RESULTS_CHANNEL_IDS=channel_id_1,channel_id_2
MYTHIC_PASSWORD=choose_any_admin_password
ADMIN_ID=your_discord_user_id
```

**How to get Discord IDs:**
- Enable **Developer Mode** in Discord (Settings > Advanced > Developer Mode)
- **Guild ID:** Right-click your server name > Copy Server ID
- **Channel ID:** Right-click the results channel > Copy Channel ID
- **Client ID:** Discord Developer Portal > General Information > Application ID
- **Admin ID:** Right-click yourself in Discord > Copy User ID

### 5. Start the bot

```bash
python bot.py
```

You should see:
```
Database initialized.
Logged in as YourBot#1234 (ID: 123456789)
Cached 852 map images from BrawlAPI.
```

Slash commands are synced automatically on startup.

## Commands

| Command | Description |
|---------|-------------|
| `/add <player_tag>` | Add a Brawl Stars player to the tracker (e.g. `/add #2YQ8V09CL`) |
| `/mythic <player_name> <password>` | Toggle best-of-3 ranked tracking for a player (password required) |
| `/winrate <name>` | Show set-based win/loss stats with per-brawler breakdown |
| `/carry <name>` | Show win rates with each tracked teammate |
| `/reset <name>` | Clear all battle/set history for a player (admin only) |

## How It Works

1. **Add players** with `/add` — validates the tag against the Brawl Stars API and stores them
2. **Enable tracking** with `/mythic` — activates polling for that player's ranked games
3. **Automatic detection** — every 60 seconds, the bot fetches battle logs and groups new soloRanked games into bo3 sets
4. **Live posting** — when a set completes (someone reaches 2 wins), a rich embed is posted to your results channels
5. **Stats tracking** — use `/winrate` for set-based stats or `/carry` to see teammate synergies

### Best-of-3 Set Detection

The Brawl Stars API reports individual games, not sets. The bot infers bo3 sets by grouping consecutive soloRanked battles within a 5-minute window. A set completes when one side reaches 2 wins. Sets open for more than 30 minutes are auto-closed.

These constants are configurable in `config.py`:
- `SET_TIME_GAP_MINUTES` (default: 5) — max gap between games in the same set
- `STALE_SET_MINUTES` (default: 30) — auto-close incomplete sets after this long

## Project Structure

```
brawlbot-py/
├── bot.py              # Entry point — loads cogs, syncs commands
├── config.py           # Environment variables and constants
├── db.py               # SQLite schema and async query functions
├── api.py              # Brawl Stars API client
├── embeds.py           # Discord embed builders for match results
├── map_cache.py        # Map image caching from BrawlAPI
├── utils.py            # Tag normalization, time helpers, emoji maps
├── cogs/
│   └── tracker.py      # All commands + 60-second polling loop
├── data/               # SQLite database (auto-created, gitignored)
├── requirements.txt
└── Procfile            # For Railway/Render deployment
```

## Deployment

The bot needs a host that runs a long-lived process (not serverless). Recommended options:

- **Railway** — Connect your GitHub repo, set env vars in dashboard, attach a volume at `data/` for SQLite
- **Render** — Create a Background Worker (not Web Service), add a Disk for persistence
- **Local with pm2** — `pip install` and run with a process manager

The `Procfile` is included for Railway/Render: `worker: python bot.py`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Missing Access` on startup | Bot hasn't been invited with `applications.commands` scope — re-invite |
| `403` from Brawl Stars API | API key is IP-locked — regenerate at developer.brawlstars.com |
| No matches appearing | Battle logs can take up to 30 minutes to appear in the API; ensure the player has mythic mode enabled |
| Sets splitting incorrectly | Increase `SET_TIME_GAP_MINUTES` in `config.py` |

## License

MIT
