import json
import uuid

import discord
from discord import app_commands
from discord.ext import commands, tasks

import db
from api import get_player as api_get_player, get_battle_log, BrawlAPIError
from config import SET_TIME_GAP_MINUTES, STALE_SET_MINUTES, RESULTS_CHANNEL_IDS, MYTHIC_PASSWORD, PIC_ADMIN_ID
from embeds import build_set_embed
from map_cache import load_map_data
from utils import normalize_tag, time_diff_minutes, format_win_rate


class TrackerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._is_polling = False

    async def cog_load(self):
        await load_map_data()
        self.poll_ranked.start()

    async def cog_unload(self):
        self.poll_ranked.cancel()

    # ── Autocomplete helper ──

    async def _player_name_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        names = await db.get_all_player_names()
        filtered = [n for n in names if current.lower() in n.lower()][:25]
        return [app_commands.Choice(name=n, value=n) for n in filtered]

    # ── /add ──

    @app_commands.command(name="add", description="Add a Brawl Stars player to the tracker")
    @app_commands.describe(player_tag="The player tag (e.g. #2YQ8V09CL)")
    async def add(self, interaction: discord.Interaction, player_tag: str):
        await interaction.response.defer()
        tag = normalize_tag(player_tag)

        try:
            player = await api_get_player(tag)
        except BrawlAPIError as e:
            if e.status == 404:
                await interaction.followup.send(f"\u274c Player with tag `{tag}` not found. Double-check the tag.")
            else:
                await interaction.followup.send("\u274c Failed to fetch player data from Brawl Stars API.")
            return

        await db.add_player(tag, player["name"])

        embed = discord.Embed(color=0x00C8FF, title="\u2705 Player Added")
        embed.description = f"**{player['name']}** has been added to the tracker."
        embed.add_field(name="\U0001f3f7\ufe0f Tag", value=tag, inline=True)
        embed.add_field(name="\U0001f3c6 Trophies", value=str(player["trophies"]), inline=True)
        embed.add_field(name="\U0001f4ca Highest", value=str(player["highestTrophies"]), inline=True)
        embed.set_footer(text="Use /mythic to enable ranked tracking")

        await interaction.followup.send(embed=embed)

    # ── /mythic ──

    @app_commands.command(name="mythic", description="Toggle mythic (best-of-3) tracking for a player")
    @app_commands.describe(player_name="The player's in-game name", password="Admin password")
    @app_commands.autocomplete(player_name=_player_name_autocomplete)
    async def mythic(self, interaction: discord.Interaction, player_name: str, password: str):
        await interaction.response.defer(ephemeral=True)

        if password != MYTHIC_PASSWORD:
            await interaction.followup.send("\u274c Incorrect password.", ephemeral=True)
            return

        player = await db.get_player_by_name(player_name)
        if not player:
            await interaction.followup.send(
                f"\u274c Player **{player_name}** not found. Add them first with `/add`.",
                ephemeral=True,
            )
            return

        new_value = await db.toggle_mythic(player["tag"])
        status = "enabled" if new_value else "disabled"
        emoji = "\U0001f7e2" if new_value else "\U0001f534"

        embed = discord.Embed(
            color=0x57F287 if new_value else 0xED4245,
            title=f"{emoji} Mythic Mode {status.capitalize()}",
            description=(
                f"**{player['name']}** is now being tracked in **best-of-3** ranked mode."
                if new_value
                else f"**{player['name']}** has been removed from active ranked tracking."
            ),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /carry ──

    @app_commands.command(name="carry", description="Show win rates with each tracked teammate")
    @app_commands.describe(name="The player's in-game name")
    @app_commands.autocomplete(name=_player_name_autocomplete)
    async def carry(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()

        player = await db.get_player_by_name(name)
        if not player:
            await interaction.followup.send(f"\u274c Player **{name}** not found.")
            return

        # Get all tracked player tags
        all_player_names = await db.get_all_player_names()
        all_players_db = db.get_db()
        cursor = await all_players_db.execute("SELECT tag, name FROM players")
        all_players = await cursor.fetchall()
        tracked_tags = {p["tag"]: p["name"] for p in all_players}

        battles = await db.get_all_battles_for_player(player["tag"])
        if not battles:
            await interaction.followup.send(f"\U0001f4ed No ranked battles recorded for **{player['name']}** yet.")
            return

        teammate_stats: dict[str, dict] = {}

        for battle in battles:
            try:
                teams = json.loads(battle["teams_json"]) if battle["teams_json"] else None
            except (json.JSONDecodeError, TypeError):
                continue
            if not teams or len(teams) < 2:
                continue

            # Find player's team
            player_team = None
            for team in teams:
                for p in team:
                    if p.get("tag") == player["tag"]:
                        player_team = team
                        break
                if player_team:
                    break
            if not player_team:
                continue

            for teammate in player_team:
                t_tag = teammate.get("tag")
                if t_tag == player["tag"] or t_tag not in tracked_tags:
                    continue

                if t_tag not in teammate_stats:
                    teammate_stats[t_tag] = {"name": tracked_tags[t_tag], "wins": 0, "losses": 0}

                stats = teammate_stats[t_tag]
                if battle["result"] == "victory":
                    stats["wins"] += 1
                elif battle["result"] == "defeat":
                    stats["losses"] += 1

        if not teammate_stats:
            await interaction.followup.send(
                f"\U0001f4ed **{player['name']}** hasn't played with any other tracked players yet."
            )
            return

        sorted_stats = sorted(
            teammate_stats.values(),
            key=lambda s: s["wins"] / (s["wins"] + s["losses"]) if (s["wins"] + s["losses"]) > 0 else 0,
            reverse=True,
        )

        def get_win_rate_bar(rate: float) -> str:
            filled = round(rate * 10)
            return "\U0001f7e9" * filled + "\u2b1b" * (10 - filled)

        lines = []
        for i, s in enumerate(sorted_stats):
            total = s["wins"] + s["losses"]
            rate = s["wins"] / total if total > 0 else 0
            wr = format_win_rate(s["wins"], total)
            bar = get_win_rate_bar(rate)
            medal = "\U0001f451" if i == 0 else ("\U0001f480" if i == len(sorted_stats) - 1 and len(sorted_stats) > 1 else "\u2022")
            lines.append(f"{medal} **{s['name']}** \u2014 {s['wins']}W {s['losses']}L ({wr})\n  {bar}  {total} games")

        embed = discord.Embed(
            color=0x00C8FF,
            title=f"\U0001f91d {player['name']} \u2014 Teammate Win Rates",
            description="\n\n".join(lines),
        )
        embed.set_footer(text=f"Based on {len(battles)} tracked games")
        await interaction.followup.send(embed=embed)

    # ── /reset ──

    @app_commands.command(name="reset", description="Reset all battle history for a player")
    @app_commands.describe(name="The player's in-game name")
    @app_commands.autocomplete(name=_player_name_autocomplete)
    async def reset(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)

        if str(interaction.user.id) != PIC_ADMIN_ID:
            await interaction.followup.send("\u274c Only the bot owner can use this command.", ephemeral=True)
            return

        player = await db.get_player_by_name(name)
        if not player:
            await interaction.followup.send(f"\u274c Player **{name}** not found.", ephemeral=True)
            return

        battles_deleted, sets_deleted = await db.reset_player_history(player["tag"])

        embed = discord.Embed(color=0xED4245, title="\U0001f5d1\ufe0f History Reset")
        embed.description = f"Cleared all data for **{player['name']}**"
        embed.add_field(name="Battles Deleted", value=str(battles_deleted), inline=True)
        embed.add_field(name="Sets Deleted", value=str(sets_deleted), inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /winrate ──

    @app_commands.command(name="winrate", description="Show ranked win/loss stats for a player")
    @app_commands.describe(name="The player's in-game name")
    @app_commands.autocomplete(name=_player_name_autocomplete)
    async def winrate(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()

        player = await db.get_player_by_name(name)
        if not player:
            await interaction.followup.send(f"\u274c Player **{name}** not found.")
            return

        stats = await db.get_player_stats(player["tag"])
        overall = stats["overall"]

        if overall["total"] == 0:
            await interaction.followup.send(f"\U0001f4ed No ranked battles recorded for **{player['name']}** yet.")
            return

        wr = format_win_rate(overall["wins"], overall["total"])
        star_rate = format_win_rate(overall["star_player_count"], overall["total"])

        overall_lines = [
            f"\U0001f3c6 **Sets Won:** {overall['wins']}",
            f"\U0001f480 **Sets Lost:** {overall['losses']}",
            f"\U0001f4ca **Win Rate:** {wr}",
            "",
            f"\u2b50 **Star Player:** {overall['star_player_count']}/{overall['total']} ({star_rate})",
        ]

        brawler_lines = []
        for b in stats["byBrawler"][:15]:
            bwr = format_win_rate(b["wins"], b["total"])
            sp = f" \u2b50{b['star_player_count']}" if b["star_player_count"] > 0 else ""
            brawler_lines.append(f"**{b['brawler_name']}**: {b['wins']}W-{b['losses']}L ({bwr}){sp}")

        if not brawler_lines:
            brawler_lines.append("No brawler data yet.")

        embed = discord.Embed(color=0xFFD700, title=f"\U0001f4c8 {player['name']} \u2014 Ranked Stats")
        embed.add_field(name="\U0001f3af Overall Record", value="\n".join(overall_lines), inline=True)
        embed.add_field(name="\U0001f3ae Top Brawlers", value="\n".join(brawler_lines), inline=True)
        embed.set_footer(text=f"{overall['total']} sets tracked")

        await interaction.followup.send(embed=embed)

    # ── Polling Loop ──

    @tasks.loop(seconds=60)
    async def poll_ranked(self):
        if self._is_polling:
            return
        self._is_polling = True

        try:
            players = await db.get_all_mythic_players()
            if not players:
                return

            for player in players:
                try:
                    await self._process_player(player)
                except BrawlAPIError as e:
                    if e.status == 429:
                        print("Rate limited by Brawl Stars API. Skipping remaining players this cycle.")
                        break
                    print(f"Error processing {player['name']} ({player['tag']}): {e}")
                except Exception as e:
                    print(f"Error processing {player['name']} ({player['tag']}): {e}")

            await self._post_completed_sets()
            await self._close_stale_sets()
        finally:
            self._is_polling = False

    @poll_ranked.before_loop
    async def before_poll(self):
        await self.bot.wait_until_ready()

    async def _process_player(self, player):
        battles = await get_battle_log(player["tag"])
        ranked_battles = [b for b in battles if b.get("battle", {}).get("type") == "soloRanked"]

        if not ranked_battles:
            return

        new_count = 0
        for raw in ranked_battles:
            battle_data = self._extract_battle_data(raw, player["tag"])
            if not battle_data:
                continue
            changes = await db.insert_battle(battle_data)
            if changes > 0:
                new_count += 1

        if new_count > 0:
            print(f"\U0001f4e5 {player['name']}: {new_count} new ranked battle(s) found.")

        await self._group_battles_into_sets(player["tag"])

    def _extract_battle_data(self, raw: dict, player_tag: str) -> dict | None:
        battle = raw.get("battle")
        event = raw.get("event")
        if not battle or not event:
            return None

        player_brawler = None
        is_star_player = False

        teams = battle.get("teams", [])
        for team in teams:
            for p in team:
                if p.get("tag") == player_tag:
                    player_brawler = p.get("brawler")

        star = battle.get("starPlayer")
        if star and star.get("tag") == player_tag:
            is_star_player = True

        return {
            "player_tag": player_tag,
            "battle_time": raw.get("battleTime"),
            "battle_type": battle.get("type"),
            "mode": event.get("mode") or battle.get("mode"),
            "map": event.get("map"),
            "result": battle.get("result"),
            "is_star_player": is_star_player,
            "brawler_name": player_brawler.get("name") if player_brawler else None,
            "brawler_id": player_brawler.get("id") if player_brawler else None,
            "duration": battle.get("duration"),
            "teams_json": json.dumps(teams) if teams else None,
        }

    async def _group_battles_into_sets(self, player_tag: str):
        unassigned = await db.get_unassigned_battles(player_tag)
        if not unassigned:
            return

        for battle in unassigned:
            active_set = await db.get_incomplete_set(player_tag)

            if active_set:
                set_battles = await db.get_set_battles(active_set["id"])
                last_battle = set_battles[-1] if set_battles else None

                if last_battle and time_diff_minutes(last_battle["battle_time"], battle["battle_time"]) <= SET_TIME_GAP_MINUTES:
                    game_number = len(set_battles) + 1
                    await db.assign_battle_to_set(battle["id"], active_set["id"], game_number)

                    new_wins = active_set["wins"] + (1 if battle["result"] == "victory" else 0)
                    new_losses = active_set["losses"] + (1 if battle["result"] == "defeat" else 0)
                    await db.update_set_score(active_set["id"], new_wins, new_losses)
                    continue

            # Create a new set
            set_id = str(uuid.uuid4())
            await db.create_set(set_id, player_tag, battle["battle_time"])
            await db.assign_battle_to_set(battle["id"], set_id, 1)

            wins = 1 if battle["result"] == "victory" else 0
            losses = 1 if battle["result"] == "defeat" else 0
            await db.update_set_score(set_id, wins, losses)

    async def _post_completed_sets(self):
        if not RESULTS_CHANNEL_IDS:
            return

        channels = []
        for cid in RESULTS_CHANNEL_IDS:
            ch = self.bot.get_channel(int(cid))
            if not ch:
                try:
                    ch = await self.bot.fetch_channel(int(cid))
                except Exception:
                    print(f"Results channel {cid} not found.")
                    continue
            channels.append(ch)

        if not channels:
            return

        unposted = await db.get_unposted_completed_sets()

        for s in unposted:
            try:
                battles = await db.get_set_battles(s["id"])

                # Only post proper bo3 sets
                if len(battles) < 2 or (s["wins"] < 2 and s["losses"] < 2):
                    await db.mark_set_posted(s["id"])
                    continue

                embed = build_set_embed(s, battles, s["player_tag"])

                for channel in channels:
                    try:
                        await channel.send(embed=embed)
                    except Exception as e:
                        print(f"Failed to post to {channel.id}: {e}")

                await db.mark_set_posted(s["id"])
                await db.mark_battles_posted(s["id"])
                print(f"\U0001f4e4 Posted set result for {s['player_tag']}: {s['result']} ({s['wins']}-{s['losses']})")
            except Exception as e:
                print(f"Failed to post set {s['id']}: {e}")

    async def _close_stale_sets(self):
        stale = await db.get_stale_sets(STALE_SET_MINUTES)
        for s in stale:
            battles = await db.get_set_battles(s["id"])
            if len(battles) < 2:
                await db.force_complete_set(s["id"])
                await db.mark_set_posted(s["id"])
            else:
                await db.force_complete_set(s["id"])
                print(f"\u23f0 Auto-closed stale set {s['id']} for {s['player_tag']} ({s['wins']}-{s['losses']})")


async def setup(bot: commands.Bot):
    await bot.add_cog(TrackerCog(bot))
