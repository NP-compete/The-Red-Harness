import { useEffect, useState } from 'react';

import { buildAppPath } from '../lib/app-paths';
import type { ReasoningProfile } from '../lib/reasoning-choice';

/**
 * The ways of answering this deployment offers, or none.
 *
 * None is the ordinary answer, not a failure: the agent returns
 * an empty list when the profiles it has would all send the same
 * request, and the composer then leaves the control out rather
 * than offering a menu that changes nothing.
 *
 * Asked once for the whole page, and the answer kept. Two
 * reasons, and the second is the one that bit:
 *
 * - Several components want this, and it is the same answer.
 * - A component mounting later — the stream hook is created when
 *   a conversation starts, which is the same moment the first
 *   message is sent — would otherwise begin its own fetch and
 *   send that first message before the answer arrived. The
 *   conversation's chosen profile would be dropped on its first
 *   turn only, which is the kind of fault nobody reports because
 *   the second message works.
 */
let answered: ReasoningProfile[] | null = null;
let asking: Promise<ReasoningProfile[]> | null = null;

async function ask(): Promise<ReasoningProfile[]> {
  try {
    const res = await fetch(buildAppPath('/api/proxy/agent/reasoning-profiles'), {
      credentials: 'same-origin',
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) return [];
    const body = (await res.json()) as { profiles?: ReasoningProfile[] };
    return Array.isArray(body.profiles) ? body.profiles : [];
  } catch {
    // Offering no choice is better than offering one that fails.
    return [];
  }
}

/** Forget the cached answer. For tests, which must not share one. */
export function forgetReasoningProfiles(): void {
  answered = null;
  asking = null;
}

export function useReasoningProfiles(): ReasoningProfile[] {
  const [profiles, setProfiles] = useState<ReasoningProfile[]>(() => answered ?? []);

  useEffect(() => {
    if (answered) {
      setProfiles(answered);
      return;
    }
    let alive = true;
    asking ??= ask().then((found) => {
      answered = found;
      return found;
    });
    void asking.then((found) => {
      if (alive) setProfiles(found);
    });
    return () => {
      alive = false;
    };
  }, []);

  return profiles;
}
