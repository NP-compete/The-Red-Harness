/**
 * A record of who changed which feature flag, and to what.
 *
 * These flags decide what every person using this deployment can
 * see and do, and until now a change left nothing behind but a log
 * line with no author. "Memory was on last week" is a question
 * somebody eventually asks, and the answer has to exist before they
 * ask it.
 *
 * Recording must never cost a change: if the trail cannot be
 * written, the change still stands and the failure is logged. An
 * override that silently fails because its audit entry did would be
 * a worse outcome than an incomplete trail.
 */

import { getRedisClient } from './redis.js';

const KEY = 'ui:feature-changes';

// Enough to answer "what happened recently" without becoming a
// store in its own right. A deployment that needs more than this
// needs a real audit sink, not a longer list.
const KEEP = 200;

export interface FlagChange {
  key: string;
  /** What it was, or null if nothing had set it. */
  from: boolean | null;
  to: boolean;
}

export interface RecordedChange extends FlagChange {
  who: string;
  when: string;
}

/** What a write actually changes, ignoring values rewritten unchanged. */
export function changesFrom(
  before: Record<string, boolean>,
  written: Record<string, boolean>,
): FlagChange[] {
  return Object.entries(written)
    .filter(([key, to]) => (key in before ? before[key] !== to : true))
    .map(([key, to]) => ({ key, from: key in before ? before[key] : null, to }));
}

export async function recordFlagChanges(
  who: string,
  changes: FlagChange[],
): Promise<void> {
  if (changes.length === 0) return;
  const redis = getRedisClient();
  if (!redis) return;

  const when = new Date().toISOString();
  try {
    for (const change of changes) {
      // Unnamed rather than dropped: a change by somebody the
      // session could not identify is the one most worth keeping.
      await redis.lpush(KEY, JSON.stringify({ ...change, who: who || 'unknown', when }));
    }
    await redis.ltrim(KEY, 0, KEEP - 1);
  } catch {
    // The change itself has already been made and stands.
  }
}

/** Recent changes, newest first. */
export async function readFlagChanges(limit = 20): Promise<RecordedChange[]> {
  const redis = getRedisClient();
  if (!redis) return [];

  try {
    const raw = await redis.lrange(KEY, 0, limit - 1);
    return raw
      .map((entry: string) => {
        try {
          return JSON.parse(entry) as RecordedChange;
        } catch {
          return null;
        }
      })
      .filter((entry: RecordedChange | null): entry is RecordedChange => entry !== null);
  } catch {
    return [];
  }
}
