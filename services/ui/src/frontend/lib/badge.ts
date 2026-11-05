export interface BadgeThread {
  id: string;
  /** Stopped, waiting for a person. Not merely running. */
  awaitingUser: boolean;
}

export interface Badge {
  show: boolean;
  count: number;
}

/**
 * What the dock icon should say.
 *
 * It answers one question: how many conversations are stopped
 * waiting for me. A run in progress is not an obligation, and a
 * badge that counts activity rather than obligation is a badge
 * people stop reading — which costs the one that mattered.
 *
 * Counted by thread, because a conversation that raised two
 * interrupts is still one thing to go and look at.
 */
export function badgeFor(
  threads: BadgeThread[],
  {
    enabled,
    // A badge is notification-shaped, so it hides behind the same
    // platform gate. Part of the decision rather than something
    // every call site has to remember, because the one that forgets
    // is the hole.
    supported = true,
  }: { enabled: boolean; supported?: boolean },
): Badge {
  if (!enabled || !supported) return { show: false, count: 0 };

  const waiting = new Set(
    threads.filter((thread) => thread.awaitingUser).map((thread) => thread.id),
  );
  return { show: waiting.size > 0, count: waiting.size };
}

/** The two calls a browser might offer, either of which may be absent. */
interface Badging {
  setAppBadge?: (n?: number) => Promise<void>;
  clearAppBadge?: () => Promise<void>;
}

/**
 * Put the count on the icon, or take it off.
 *
 * Separate from the decision above so both can be read and
 * tested without a browser, which is the rule the service
 * worker follows for the same reason: this is the hardest
 * code here to observe once it is running.
 *
 * Clearing, never setting zero. A zero still paints a mark in
 * some browsers, and a mark that does not go away is why
 * somebody stops reading it — including on the day it was
 * right.
 *
 * Every failure is swallowed. Most browsers have no badging at
 * all, the calls return promises that may be refused, and this
 * runs on every state change: an unhandled rejection here fills
 * the console on a feature nobody asked about, and the console
 * is where somebody looks when something else is wrong.
 */
export function applyBadge(nav: Navigator | undefined, badge: Badge): void {
  const badging = nav as (Navigator & Badging) | undefined;
  try {
    const call = badge.show
      ? badging?.setAppBadge?.(badge.count)
      : badging?.clearAppBadge?.();
    void call?.catch(() => undefined);
  } catch {
    // A browser that throws rather than rejecting.
  }
}
