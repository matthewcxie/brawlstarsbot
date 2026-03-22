/**
 * Normalize a Brawl Stars player tag to uppercase with # prefix.
 */
function normalizeTag(tag) {
  let cleaned = tag.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
  return '#' + cleaned;
}

/**
 * Parse Brawl Stars battle time string to a Date.
 * Format: "20240315T120000.000Z"
 */
function parseBattleTime(timeStr) {
  // Insert dashes and colons: "2024-03-15T12:00:00.000Z"
  const formatted = timeStr.replace(
    /(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})/,
    '$1-$2-$3T$4:$5:$6',
  );
  return new Date(formatted);
}

/**
 * Get the absolute time difference in minutes between two battle time strings.
 */
function timeDiffMinutes(time1, time2) {
  const d1 = parseBattleTime(time1);
  const d2 = parseBattleTime(time2);
  return Math.abs(d1 - d2) / 60_000;
}

/**
 * Emoji for a match result.
 */
function resultEmoji(result) {
  switch (result) {
    case 'victory': return '🟢';
    case 'defeat': return '🔴';
    default: return '⚪';
  }
}

/**
 * Emoji for game modes.
 */
function modeEmoji(mode) {
  const map = {
    gemGrab: '💎',
    brawlBall: '⚽',
    heist: '🔐',
    bounty: '⭐',
    siege: '🔧',
    hotZone: '🔥',
    knockout: '💀',
    wipeout: '💥',
    payload: '🚛',
    snowtelThieves: '❄️',
    paintBrawl: '🎨',
    trophy_thieves: '🏆',
  };
  return map[mode] || '🎮';
}

/**
 * Format a win rate percentage.
 */
function formatWinRate(wins, total) {
  if (total === 0) return '0%';
  return ((wins / total) * 100).toFixed(1) + '%';
}

/**
 * Capitalize the first letter of each word and lower the rest.
 */
function formatModeName(mode) {
  return mode
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, s => s.toUpperCase())
    .trim();
}

module.exports = {
  normalizeTag,
  parseBattleTime,
  timeDiffMinutes,
  resultEmoji,
  modeEmoji,
  formatWinRate,
  formatModeName,
};
