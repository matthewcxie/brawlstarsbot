import os
import aiosqlite

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "bot.db")

_db: aiosqlite.Connection | None = None


async def init_db() -> aiosqlite.Connection:
    global _db
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode = WAL")
    await _db.execute("PRAGMA foreign_keys = ON")

    await _db.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            tag TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            is_mythic INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS battles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_tag TEXT NOT NULL,
            battle_time TEXT NOT NULL,
            battle_type TEXT,
            mode TEXT,
            map TEXT,
            result TEXT,
            is_star_player INTEGER DEFAULT 0,
            brawler_name TEXT,
            brawler_id INTEGER,
            duration INTEGER,
            teams_json TEXT,
            set_id TEXT,
            set_game_number INTEGER,
            posted INTEGER DEFAULT 0,
            UNIQUE(player_tag, battle_time)
        );

        CREATE TABLE IF NOT EXISTS sets (
            id TEXT PRIMARY KEY,
            player_tag TEXT NOT NULL,
            result TEXT,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            started_at TEXT,
            completed INTEGER DEFAULT 0,
            posted INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS pic_allowed_users (
            user_id TEXT PRIMARY KEY,
            added_by TEXT NOT NULL,
            added_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS pic_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            image_url TEXT NOT NULL,
            added_by TEXT NOT NULL,
            added_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS pic_daily (
            date TEXT PRIMARY KEY,
            pic_id INTEGER NOT NULL,
            FOREIGN KEY (pic_id) REFERENCES pic_library(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS pic_aliases (
            alias TEXT PRIMARY KEY,
            target TEXT NOT NULL
        );
    """)

    # Migration: add battle_type column if missing
    cursor = await _db.execute("PRAGMA table_info(battles)")
    cols = [row[1] for row in await cursor.fetchall()]
    if "battle_type" not in cols:
        await _db.execute("ALTER TABLE battles ADD COLUMN battle_type TEXT")
        await _db.execute("UPDATE battles SET battle_type = 'ranked' WHERE battle_type IS NULL")

    await _db.commit()
    print("Database initialized.")
    return _db


def get_db() -> aiosqlite.Connection:
    assert _db is not None, "Database not initialized. Call init_db() first."
    return _db


# ── Player Queries ──


async def add_player(tag: str, name: str):
    db = get_db()
    await db.execute(
        "INSERT INTO players (tag, name) VALUES (?, ?) ON CONFLICT(tag) DO UPDATE SET name = excluded.name",
        (tag, name),
    )
    await db.commit()


async def get_player(tag: str):
    db = get_db()
    cursor = await db.execute("SELECT * FROM players WHERE tag = ?", (tag,))
    return await cursor.fetchone()


async def get_player_by_name(name: str):
    db = get_db()
    cursor = await db.execute("SELECT * FROM players WHERE LOWER(name) = LOWER(?)", (name,))
    return await cursor.fetchone()


async def get_all_player_names() -> list[str]:
    db = get_db()
    cursor = await db.execute("SELECT name FROM players ORDER BY name")
    rows = await cursor.fetchall()
    return [row["name"] for row in rows]


async def get_all_mythic_players():
    db = get_db()
    cursor = await db.execute("SELECT * FROM players WHERE is_mythic = 1")
    return await cursor.fetchall()


async def toggle_mythic(tag: str):
    player = await get_player(tag)
    if not player:
        return None
    new_value = 0 if player["is_mythic"] else 1
    db = get_db()
    await db.execute("UPDATE players SET is_mythic = ? WHERE tag = ?", (new_value, tag))
    await db.commit()
    return new_value


# ── Battle Queries ──


async def insert_battle(battle: dict) -> int:
    db = get_db()
    cursor = await db.execute(
        """INSERT OR IGNORE INTO battles
            (player_tag, battle_time, battle_type, mode, map, result, is_star_player,
             brawler_name, brawler_id, duration, teams_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            battle["player_tag"],
            battle["battle_time"],
            battle["battle_type"],
            battle["mode"],
            battle["map"],
            battle["result"],
            1 if battle["is_star_player"] else 0,
            battle["brawler_name"],
            battle["brawler_id"],
            battle["duration"],
            battle["teams_json"],
        ),
    )
    await db.commit()
    return cursor.rowcount


async def get_unassigned_battles(player_tag: str):
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM battles WHERE player_tag = ? AND set_id IS NULL ORDER BY battle_time ASC",
        (player_tag,),
    )
    return await cursor.fetchall()


async def assign_battle_to_set(battle_id: int, set_id: str, game_number: int):
    db = get_db()
    await db.execute(
        "UPDATE battles SET set_id = ?, set_game_number = ? WHERE id = ?",
        (set_id, game_number, battle_id),
    )
    await db.commit()


async def get_set_battles(set_id: str):
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM battles WHERE set_id = ? ORDER BY set_game_number ASC",
        (set_id,),
    )
    return await cursor.fetchall()


async def mark_battles_posted(set_id: str):
    db = get_db()
    await db.execute("UPDATE battles SET posted = 1 WHERE set_id = ?", (set_id,))
    await db.commit()


# ── Set Queries ──


async def create_set(set_id: str, player_tag: str, started_at: str):
    db = get_db()
    await db.execute(
        "INSERT INTO sets (id, player_tag, wins, losses, started_at) VALUES (?, ?, 0, 0, ?)",
        (set_id, player_tag, started_at),
    )
    await db.commit()


async def get_incomplete_set(player_tag: str):
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM sets WHERE player_tag = ? AND completed = 0 ORDER BY started_at DESC LIMIT 1",
        (player_tag,),
    )
    return await cursor.fetchone()


async def update_set_score(set_id: str, wins: int, losses: int) -> dict:
    completed = 1 if (wins >= 2 or losses >= 2) else 0
    result = ("victory" if wins >= 2 else "defeat") if completed else None
    db = get_db()
    await db.execute(
        "UPDATE sets SET wins = ?, losses = ?, completed = ?, result = ? WHERE id = ?",
        (wins, losses, completed, result, set_id),
    )
    await db.commit()
    return {"completed": bool(completed), "result": result}


async def get_unposted_completed_sets():
    db = get_db()
    cursor = await db.execute("SELECT * FROM sets WHERE completed = 1 AND posted = 0")
    return await cursor.fetchall()


async def mark_set_posted(set_id: str):
    db = get_db()
    await db.execute("UPDATE sets SET posted = 1 WHERE id = ?", (set_id,))
    await db.commit()


async def get_stale_sets(minutes_old: int):
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM sets WHERE completed = 0 AND datetime(started_at) < datetime('now', ? || ' minutes')",
        (-minutes_old,),
    )
    return await cursor.fetchall()


async def force_complete_set(set_id: str):
    db = get_db()
    cursor = await db.execute("SELECT * FROM sets WHERE id = ?", (set_id,))
    s = await cursor.fetchone()
    if not s:
        return
    result = "victory" if s["wins"] > s["losses"] else "defeat"
    await db.execute("UPDATE sets SET completed = 1, result = ? WHERE id = ?", (result, set_id))
    await db.commit()


# ── Stats Queries ──


async def get_player_stats(player_tag: str) -> dict:
    db = get_db()

    cursor = await db.execute(
        """SELECT
            COUNT(*) as total,
            SUM(CASE WHEN s.result = 'victory' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN s.result = 'defeat' THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN EXISTS (
                SELECT 1 FROM battles b WHERE b.set_id = s.id AND b.is_star_player = 1
            ) THEN 1 ELSE 0 END) as star_player_count
           FROM sets s
           WHERE s.player_tag = ? AND s.completed = 1""",
        (player_tag,),
    )
    overall = await cursor.fetchone()

    cursor = await db.execute(
        """SELECT
            b.brawler_name, b.brawler_id,
            COUNT(DISTINCT s.id) as total,
            SUM(CASE WHEN s.result = 'victory' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN s.result = 'defeat' THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN EXISTS (
                SELECT 1 FROM battles b2 WHERE b2.set_id = s.id AND b2.is_star_player = 1
            ) THEN 1 ELSE 0 END) as star_player_count
           FROM sets s
           JOIN battles b ON b.set_id = s.id AND b.set_game_number = 1
           WHERE s.player_tag = ? AND s.completed = 1
           GROUP BY b.brawler_name
           ORDER BY total DESC""",
        (player_tag,),
    )
    by_brawler = await cursor.fetchall()

    return {"overall": overall, "setStats": overall, "byBrawler": by_brawler}


async def get_all_battles_for_player(player_tag: str):
    db = get_db()
    cursor = await db.execute("SELECT * FROM battles WHERE player_tag = ?", (player_tag,))
    return await cursor.fetchall()


async def reset_player_history(player_tag: str) -> tuple[int, int]:
    db = get_db()
    c1 = await db.execute("DELETE FROM battles WHERE player_tag = ?", (player_tag,))
    c2 = await db.execute("DELETE FROM sets WHERE player_tag = ?", (player_tag,))
    await db.commit()
    return c1.rowcount, c2.rowcount


# ── Pic Allowed Users ──


async def add_allowed_user(user_id: str, added_by: str):
    db = get_db()
    await db.execute(
        "INSERT OR IGNORE INTO pic_allowed_users (user_id, added_by) VALUES (?, ?)",
        (user_id, added_by),
    )
    await db.commit()


async def remove_allowed_user(user_id: str):
    db = get_db()
    await db.execute("DELETE FROM pic_allowed_users WHERE user_id = ?", (user_id,))
    await db.commit()


async def get_all_allowed_users():
    db = get_db()
    cursor = await db.execute("SELECT * FROM pic_allowed_users")
    return await cursor.fetchall()


async def is_allowed_user(user_id: str) -> bool:
    db = get_db()
    cursor = await db.execute("SELECT 1 FROM pic_allowed_users WHERE user_id = ?", (user_id,))
    return await cursor.fetchone() is not None


# ── Pic Library ──


async def add_pic(name: str, image_url: str, added_by: str):
    db = get_db()
    await db.execute(
        "INSERT INTO pic_library (name, image_url, added_by) VALUES (?, ?, ?)",
        (name, image_url, added_by),
    )
    await db.commit()


async def remove_pic(pic_id: int):
    db = get_db()
    await db.execute("DELETE FROM pic_library WHERE id = ?", (pic_id,))
    await db.commit()


async def resolve_alias(name: str) -> str:
    db = get_db()
    cursor = await db.execute("SELECT target FROM pic_aliases WHERE alias = LOWER(?)", (name,))
    row = await cursor.fetchone()
    return row["target"] if row else name


async def get_pics_by_name(name: str):
    resolved = await resolve_alias(name)
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM pic_library WHERE LOWER(name) = LOWER(?) ORDER BY id",
        (resolved,),
    )
    return await cursor.fetchall()


async def get_random_pic_by_name(name: str):
    resolved = await resolve_alias(name)
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM pic_library WHERE LOWER(name) = LOWER(?) ORDER BY RANDOM() LIMIT 1",
        (resolved,),
    )
    return await cursor.fetchone()


async def get_random_pic():
    db = get_db()
    cursor = await db.execute("SELECT * FROM pic_library ORDER BY RANDOM() LIMIT 1")
    return await cursor.fetchone()


async def get_all_pic_names():
    db = get_db()
    cursor = await db.execute(
        "SELECT LOWER(name) as name, COUNT(*) as count FROM pic_library GROUP BY LOWER(name) ORDER BY name"
    )
    return await cursor.fetchall()


async def get_pic_by_id(pic_id: int):
    db = get_db()
    cursor = await db.execute("SELECT * FROM pic_library WHERE id = ?", (pic_id,))
    return await cursor.fetchone()


# ── Pic Daily ──


async def set_daily_pic(date: str, pic_id: int):
    db = get_db()
    await db.execute(
        "INSERT OR REPLACE INTO pic_daily (date, pic_id) VALUES (?, ?)",
        (date, pic_id),
    )
    await db.commit()


async def get_daily_pic(date: str):
    db = get_db()
    cursor = await db.execute(
        """SELECT pd.date, pd.pic_id, pl.name, pl.image_url
           FROM pic_daily pd
           JOIN pic_library pl ON pd.pic_id = pl.id
           WHERE pd.date = ?""",
        (date,),
    )
    return await cursor.fetchone()


# ── Pic Aliases (raw queries for merge/remove) ──


async def add_alias(alias: str, target: str):
    db = get_db()
    await db.execute(
        "INSERT OR REPLACE INTO pic_aliases (alias, target) VALUES (?, ?)",
        (alias, target),
    )
    await db.commit()


async def get_alias(name: str):
    db = get_db()
    cursor = await db.execute("SELECT * FROM pic_aliases WHERE alias = ?", (name,))
    return await cursor.fetchone()


async def delete_alias(name: str):
    db = get_db()
    await db.execute("DELETE FROM pic_aliases WHERE alias = ?", (name,))
    await db.commit()


async def get_all_aliases() -> list[str]:
    db = get_db()
    cursor = await db.execute("SELECT alias FROM pic_aliases")
    rows = await cursor.fetchall()
    return [row["alias"] for row in rows]


async def count_pics_by_name(name: str) -> int:
    db = get_db()
    cursor = await db.execute(
        "SELECT COUNT(*) as count FROM pic_library WHERE LOWER(name) = ?", (name,)
    )
    row = await cursor.fetchone()
    return row["count"]


async def delete_pics_by_name(name: str) -> int:
    db = get_db()
    cursor = await db.execute("DELETE FROM pic_library WHERE LOWER(name) = ?", (name,))
    await db.commit()
    return cursor.rowcount


async def delete_aliases_for_target(target: str):
    db = get_db()
    await db.execute("DELETE FROM pic_aliases WHERE target = ?", (target,))
    await db.commit()
