export interface UpdateDecision {
  action: 'none' | 'offer';
  /** Applying it reloads the page, which the offer has to say. */
  reloads: boolean;
}

/**
 * What to do about a new version waiting to take over.
 *
 * Two failures, in opposite directions. Swapping the application
 * out mid-answer loses what is on the screen — a half-written
 * message, an interrupt somebody was about to approve. Leaving
 * somebody on a stale version indefinitely is the other, and it is
 * quieter, so it is the one that actually happens.
 *
 * So the new version is never applied on its own, never offered
 * while a run is in flight, and not offered again once somebody has
 * said not now. They will get it on their next visit regardless.
 */
export function updateDecision({
  waiting,
  busy,
  dismissed,
}: {
  waiting: boolean;
  /** A run is in flight, so the screen has something to lose. */
  busy: boolean;
  dismissed: boolean;
}): UpdateDecision {
  if (!waiting || busy || dismissed) {
    return { action: 'none', reloads: true };
  }
  return { action: 'offer', reloads: true };
}
