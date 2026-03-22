const Database = require('better-sqlite3');
const path = require('node:path');

const DB_PATH = path.join(__dirname, '..', 'data', 'bot.db');
let db;

function initDb() {
  db = new Database(DB_PATH);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');

  db.exec(`
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
  `);

  console.log('Database initialized.');
  return db;
}

function getDb() {
  return db;
}

// ── Player Queries ──

function addPlayer(tag, name) {
  const stmt = db.prepare(`
    INSERT INTO players (tag, name) VALUES (?, ?)
    ON CONFLICT(tag) DO UPDATE SET name = excluded.name
  `);
  return stmt.run(tag, name);
}

function getPlayer(tag) {
  return db.prepare('SELECT * FROM players WHERE tag = ?').get(tag);
}

function getPlayerByName(name) {
  return db.prepare('SELECT * FROM players WHERE LOWER(name) = LOWER(?)').get(name);
}

function getAllPlayerNames() {
  return db.prepare('SELECT name FROM players ORDER BY name').all().map(r => r.name);
}

function getAllMythicPlayers() {
  return db.prepare('SELECT * FROM players WHERE is_mythic = 1').all();
}

function toggleMythic(tag) {
  const player = getPlayer(tag);
  if (!player) return null;
  const newValue = player.is_mythic ? 0 : 1;
  db.prepare('UPDATE players SET is_mythic = ? WHERE tag = ?').run(newValue, tag);
  return newValue;
}

// ── Battle Queries ──

function insertBattle(battle) {
  const stmt = db.prepare(`
    INSERT OR IGNORE INTO battles
      (player_tag, battle_time, mode, map, result, is_star_player,
       brawler_name, brawler_id, duration, teams_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  return stmt.run(
    battle.player_tag,
    battle.battle_time,
    battle.mode,
    battle.map,
    battle.result,
    battle.is_star_player ? 1 : 0,
    battle.brawler_name,
    battle.brawler_id,
    battle.duration,
    battle.teams_json,
  );
}

function getUnassignedBattles(playerTag) {
  return db.prepare(`
    SELECT * FROM battles
    WHERE player_tag = ? AND set_id IS NULL
    ORDER BY battle_time ASC
  `).all(playerTag);
}

function assignBattleToSet(battleId, setId, gameNumber) {
  db.prepare(`
    UPDATE battles SET set_id = ?, set_game_number = ? WHERE id = ?
  `).run(setId, gameNumber, battleId);
}

function getSetBattles(setId) {
  return db.prepare(`
    SELECT * FROM battles WHERE set_id = ? ORDER BY set_game_number ASC
  `).all(setId);
}

function markBattlesPosted(setId) {
  db.prepare('UPDATE battles SET posted = 1 WHERE set_id = ?').run(setId);
}

// ── Set Queries ──

function createSet(id, playerTag, startedAt) {
  db.prepare(`
    INSERT INTO sets (id, player_tag, wins, losses, started_at)
    VALUES (?, ?, 0, 0, ?)
  `).run(id, playerTag, startedAt);
}

function getIncompleteSet(playerTag) {
  return db.prepare(`
    SELECT * FROM sets
    WHERE player_tag = ? AND completed = 0
    ORDER BY started_at DESC LIMIT 1
  `).get(playerTag);
}

function updateSetScore(setId, wins, losses) {
  const completed = (wins >= 2 || losses >= 2) ? 1 : 0;
  const result = completed ? (wins >= 2 ? 'victory' : 'defeat') : null;
  db.prepare(`
    UPDATE sets SET wins = ?, losses = ?, completed = ?, result = ? WHERE id = ?
  `).run(wins, losses, completed, result, setId);
  return { completed: !!completed, result };
}

function getUnpostedCompletedSets() {
  return db.prepare(`
    SELECT * FROM sets WHERE completed = 1 AND posted = 0
  `).all();
}

function markSetPosted(setId) {
  db.prepare('UPDATE sets SET posted = 1 WHERE id = ?').run(setId);
}

function getStaleSets(minutesOld) {
  return db.prepare(`
    SELECT * FROM sets
    WHERE completed = 0
      AND datetime(started_at) < datetime('now', ? || ' minutes')
  `).all(-minutesOld);
}

function forceCompleteSet(setId) {
  const set = db.prepare('SELECT * FROM sets WHERE id = ?').get(setId);
  if (!set) return;
  const result = set.wins > set.losses ? 'victory' : 'defeat';
  db.prepare(`
    UPDATE sets SET completed = 1, result = ? WHERE id = ?
  `).run(result, setId);
}

// ── Stats Queries ──

function getPlayerStats(playerTag) {
  const overall = db.prepare(`
    SELECT
      COUNT(*) as total,
      SUM(CASE WHEN result = 'victory' THEN 1 ELSE 0 END) as wins,
      SUM(CASE WHEN result = 'defeat' THEN 1 ELSE 0 END) as losses,
      SUM(is_star_player) as star_player_count
    FROM battles WHERE player_tag = ?
  `).get(playerTag);

  const setStats = db.prepare(`
    SELECT
      COUNT(*) as total,
      SUM(CASE WHEN result = 'victory' THEN 1 ELSE 0 END) as wins,
      SUM(CASE WHEN result = 'defeat' THEN 1 ELSE 0 END) as losses
    FROM sets WHERE player_tag = ? AND completed = 1
  `).get(playerTag);

  const byBrawler = db.prepare(`
    SELECT
      brawler_name,
      brawler_id,
      COUNT(*) as total,
      SUM(CASE WHEN result = 'victory' THEN 1 ELSE 0 END) as wins,
      SUM(CASE WHEN result = 'defeat' THEN 1 ELSE 0 END) as losses,
      SUM(is_star_player) as star_player_count
    FROM battles WHERE player_tag = ?
    GROUP BY brawler_name
    ORDER BY total DESC
  `).all(playerTag);

  return { overall, setStats, byBrawler };
}

function getAllBattlesForPlayer(playerTag) {
  return db.prepare('SELECT * FROM battles WHERE player_tag = ?').all(playerTag);
}

// ── Pic Allowed Users ──

function addAllowedUser(userId, addedBy) {
  return db.prepare(
    'INSERT OR IGNORE INTO pic_allowed_users (user_id, added_by) VALUES (?, ?)',
  ).run(userId, addedBy);
}

function removeAllowedUser(userId) {
  return db.prepare('DELETE FROM pic_allowed_users WHERE user_id = ?').run(userId);
}

function getAllAllowedUsers() {
  return db.prepare('SELECT * FROM pic_allowed_users').all();
}

function isAllowedUser(userId) {
  return !!db.prepare('SELECT 1 FROM pic_allowed_users WHERE user_id = ?').get(userId);
}

// ── Pic Library ──

function addPic(name, imageUrl, addedBy) {
  return db.prepare(
    'INSERT INTO pic_library (name, image_url, added_by) VALUES (?, ?, ?)',
  ).run(name, imageUrl, addedBy);
}

function removePic(id) {
  return db.prepare('DELETE FROM pic_library WHERE id = ?').run(id);
}

function getPicsByName(name) {
  const resolved = resolveAlias(name);
  return db.prepare(
    'SELECT * FROM pic_library WHERE LOWER(name) = LOWER(?) ORDER BY id',
  ).all(resolved);
}

function resolveAlias(name) {
  const alias = db.prepare('SELECT target FROM pic_aliases WHERE alias = LOWER(?)').get(name);
  return alias ? alias.target : name;
}

function getRandomPicByName(name) {
  const resolved = resolveAlias(name);
  return db.prepare(
    'SELECT * FROM pic_library WHERE LOWER(name) = LOWER(?) ORDER BY RANDOM() LIMIT 1',
  ).get(resolved);
}

function getRandomPic() {
  return db.prepare('SELECT * FROM pic_library ORDER BY RANDOM() LIMIT 1').get();
}

function getAllPicNames() {
  return db.prepare(
    'SELECT LOWER(name) as name, COUNT(*) as count FROM pic_library GROUP BY LOWER(name) ORDER BY name',
  ).all();
}

function getPicById(id) {
  return db.prepare('SELECT * FROM pic_library WHERE id = ?').get(id);
}

// ── Pic Daily ──

function setDailyPic(date, picId) {
  return db.prepare(
    'INSERT OR REPLACE INTO pic_daily (date, pic_id) VALUES (?, ?)',
  ).run(date, picId);
}

function getDailyPic(date) {
  return db.prepare(`
    SELECT pd.date, pd.pic_id, pl.name, pl.image_url
    FROM pic_daily pd
    JOIN pic_library pl ON pd.pic_id = pl.id
    WHERE pd.date = ?
  `).get(date);
}

module.exports = {
  initDb, getDb,
  addPlayer, getPlayer, getPlayerByName, getAllPlayerNames, getAllMythicPlayers, toggleMythic,
  insertBattle, getUnassignedBattles, assignBattleToSet, getSetBattles, markBattlesPosted,
  createSet, getIncompleteSet, updateSetScore, getUnpostedCompletedSets, markSetPosted,
  getStaleSets, forceCompleteSet,
  getPlayerStats, getAllBattlesForPlayer,
  addAllowedUser, removeAllowedUser, getAllAllowedUsers, isAllowedUser,
  addPic, removePic, getPicsByName, getRandomPicByName, getRandomPic, getAllPicNames, getPicById,
  setDailyPic, getDailyPic,
};
