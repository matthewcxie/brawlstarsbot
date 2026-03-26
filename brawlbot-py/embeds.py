import json
from datetime import datetime, timezone

import discord

from map_cache import get_map_image, get_brawler_image
from utils import result_emoji, mode_emoji, format_mode_name


def _safe_parse(json_str: str | None):
    if not json_str:
        return None
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None


def _get_brawler_summary(battle) -> str:
    teams = _safe_parse(battle["teams_json"])
    if not teams or len(teams) < 2:
        return ""

    player_team_index = 0
    for i, team in enumerate(teams):
        for p in team:
            if p.get("tag") == battle["player_tag"]:
                player_team_index = i

    opponent_team_index = 1 if player_team_index == 0 else 0

    team_brawlers = ", ".join(
        p.get("brawler", {}).get("name", "?") for p in teams[player_team_index]
    )
    opp_brawlers = ", ".join(
        p.get("brawler", {}).get("name", "?") for p in teams[opponent_team_index]
    )

    return f"\U0001f535 {team_brawlers}\n\U0001f534 {opp_brawlers}"


def _parse_teams_with_brawlers(battle):
    teams = _safe_parse(battle["teams_json"])
    if not teams or len(teams) < 2:
        return None

    player_team_index = 0
    for i, team in enumerate(teams):
        for p in team:
            if p.get("tag") == battle["player_tag"]:
                player_team_index = i

    opponent_team_index = 1 if player_team_index == 0 else 0

    def format_player(p, is_tracked: bool) -> str:
        name = f"**{p['name']}**" if is_tracked else p["name"]
        brawler = p.get("brawler", {}).get("name", "?")
        return f"{name}\n\u2514 {brawler}"

    team1_lines = [
        format_player(p, p.get("tag") == battle["player_tag"])
        for p in teams[player_team_index]
    ]
    team2_lines = [
        format_player(p, False)
        for p in teams[opponent_team_index]
    ]

    return {"team1Lines": team1_lines, "team2Lines": team2_lines}


def build_set_embed(s, battles, player_tag: str) -> discord.Embed:
    is_victory = s["result"] == "victory"
    color = 0x57F287 if is_victory else 0xED4245
    result_text = "VICTORY" if is_victory else "DEFEAT"

    first_battle = battles[0] if battles else None
    map_name = first_battle["map"] if first_battle else "Unknown Map"
    mode = first_battle["mode"] if first_battle else "unknown"
    map_image = get_map_image(map_name)

    title_prefix = "Ranked Set"
    score_text = f"\n\n\U0001f4ca **Set Score: {s['wins']} - {s['losses']}**"

    embed = discord.Embed(
        color=color,
        title=f"{'\U0001f3c6' if is_victory else '\U0001f480'} {title_prefix} \u2014 {result_text}",
        description=f"{mode_emoji(mode)} **{format_mode_name(mode)}** on **{map_name}**{score_text}",
    )

    if map_image:
        embed.set_image(url=map_image)
        embed.set_author(name=map_name, icon_url=map_image)

    for battle in battles:
        game_result = "\u2705 Win" if battle["result"] == "victory" else "\u274c Loss"
        star_text = " \u2b50" if battle["is_star_player"] else ""
        duration = battle["duration"]
        if duration:
            mins = duration // 60
            secs = duration % 60
            dur_str = f"{mins}:{secs:02d}"
        else:
            dur_str = "?:??"

        brawler_lines = _get_brawler_summary(battle)

        embed.add_field(
            name=f"Game {battle['set_game_number']} \u2014 {game_result}{star_text}",
            value=f"\U0001f3ae {battle['brawler_name'] or 'Unknown'} \u2022 \u23f1\ufe0f {dur_str}\n{brawler_lines}",
            inline=False,
        )

    # Team rosters from the last game
    last_battle = battles[-1] if battles else None
    if last_battle:
        teams_data = _parse_teams_with_brawlers(last_battle)
        if teams_data:
            embed.add_field(name="\u200b", value="\u200b", inline=False)
            embed.add_field(
                name="\U0001f535 Your Team",
                value="\n".join(teams_data["team1Lines"]),
                inline=True,
            )
            embed.add_field(
                name="\U0001f534 Opponent",
                value="\n".join(teams_data["team2Lines"]),
                inline=True,
            )

    # Brawler icon as thumbnail
    if first_battle and first_battle["brawler_id"]:
        brawler_img = get_brawler_image(first_battle["brawler_id"])
        if brawler_img:
            embed.set_thumbnail(url=brawler_img)

    embed.timestamp = datetime.now(timezone.utc)
    return embed


def build_game_embed(battle) -> discord.Embed:
    is_victory = battle["result"] == "victory"
    color = 0x57F287 if is_victory else 0xED4245
    map_image = get_map_image(battle["map"])

    embed = discord.Embed(
        color=color,
        title=f"{result_emoji(battle['result'])} Ranked Game \u2014 {battle['map'] or 'Unknown'}",
        description=f"{mode_emoji(battle['mode'])} **{format_mode_name(battle['mode'])}**",
    )

    if map_image:
        embed.set_image(url=map_image)

    if battle["brawler_id"]:
        embed.set_thumbnail(url=get_brawler_image(battle["brawler_id"]))

    star_text = " \u2b50" if battle["is_star_player"] else ""
    embed.add_field(
        name="Result",
        value=f"{'\u2705 Win' if is_victory else '\u274c Loss'}{star_text}",
        inline=True,
    )
    embed.add_field(name="Brawler", value=battle["brawler_name"] or "Unknown", inline=True)

    teams_data = _parse_teams_with_brawlers(battle)
    if teams_data:
        embed.add_field(
            name="\U0001f535 Your Team",
            value="\n".join(teams_data["team1Lines"]),
            inline=True,
        )
        embed.add_field(
            name="\U0001f534 Opponent",
            value="\n".join(teams_data["team2Lines"]),
            inline=True,
        )

    embed.timestamp = datetime.now(timezone.utc)
    return embed
