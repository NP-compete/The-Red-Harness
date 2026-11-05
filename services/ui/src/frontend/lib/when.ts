const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/**
 * How long ago a conversation was last touched.
 *
 * Said in whichever unit is still informative: minutes for something
 * that just happened, a plain date once "43 days ago" has stopped
 * meaning anything to a reader.
 */
/**
 * When something last happened, described rather than worded.
 *
 * The words and the date format both belong to the reader's locale,
 * and neither is available out here — this ran `toLocaleDateString`
 * pinned to `en-GB`, so a French reader was shown "3 November".
 */
export type LastActive =
  | { kind: 'unknown' }
  | { kind: 'justNow' }
  | { kind: 'ago'; key: string; count: number }
  | { kind: 'date'; at: number };

export function whenLastActive(
  at: string | null | undefined,
  now: Date = new Date(),
): LastActive {
  if (!at) return { kind: 'unknown' };
  const then = Date.parse(at);
  if (Number.isNaN(then)) return { kind: 'unknown' };

  // A clock a little ahead of ours is not a reason to say anything odd.
  const ago = Math.max(0, now.getTime() - then);

  // Under a minute, so that "1 minute ago" is reachable rather
  // than swallowed by the window.
  if (ago < MINUTE) return { kind: 'justNow' };
  if (ago < HOUR) {
    return { kind: 'ago', key: 'when.minutesAgo', count: Math.floor(ago / MINUTE) };
  }
  if (ago < DAY) {
    return { kind: 'ago', key: 'when.hoursAgo', count: Math.floor(ago / HOUR) };
  }
  if (ago < 14 * DAY) {
    return { kind: 'ago', key: 'when.daysAgo', count: Math.floor(ago / DAY) };
  }

  // Past a fortnight a count stops meaning anything; the caller
  // formats the date in the reader's own locale.
  return { kind: 'date', at: then };
}
