export interface ReconnectStep {
  atMs: number;
  attempt: number;
  /** The last step: stop trying and say so. */
  giveUp: boolean;
}

/**
 * When to try reaching the agent again, and when to stop.
 *
 * The last entry is the one that matters. Without it the attempts
 * run out silently: the conversation goes on saying "Attempt 3 of
 * 3", the composer stays disabled because a run is still notionally
 * in flight, and nothing ever tells the person it is over or offers
 * them the question back.
 */
export function reconnectPlan(maxAttempts: number, intervalMs: number): ReconnectStep[] {
  const steps: ReconnectStep[] = [];
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    steps.push({ atMs: (attempt - 1) * intervalMs, attempt, giveUp: false });
  }
  return [
    ...steps,
    { atMs: maxAttempts * intervalMs, attempt: maxAttempts, giveUp: true },
  ];
}

/**
 * Whether to start the plan, given one may already be running.
 *
 * Every failed attempt arrives back through the same error path.
 * Starting again there restarts the countdown, so the run never
 * reaches the step that gives up and the composer is never handed
 * back.
 */
export function shouldSchedule({
  alreadyScheduled,
}: {
  alreadyScheduled: boolean;
}): boolean {
  return !alreadyScheduled;
}

export interface IncompleteStreamState {
  error: string | null;
  isLoading: boolean;
  isConnected: boolean;
  isReconnecting: boolean;
  reconnectAttempt: number;
  streamDroppedMidResponse: boolean;
}

const GAVE_UP = 'The agent could not be reached. Your question is still here — try again.';

/**
 * What to show when a stream closes without finishing.
 *
 * The first time this is a reconnection: the agent may simply have
 * blinked. Once the attempts are spent it is an ending, and must be
 * reported as one — otherwise giving up hands the composer back and
 * the very next closed stream takes it away again, which looks like
 * the interface arguing with itself.
 */
export function afterIncompleteStream({
  gaveUp,
  reason,
  dropped,
}: {
  gaveUp: boolean;
  reason: string;
  dropped: boolean;
}): IncompleteStreamState {
  return {
    error: gaveUp ? reason || GAVE_UP : null,
    isLoading: !gaveUp,
    isConnected: false,
    isReconnecting: !gaveUp,
    reconnectAttempt: gaveUp ? 0 : 1,
    streamDroppedMidResponse: dropped,
  };
}

/**
 * Whether the attempt loop should begin another attempt.
 *
 * The loop re-arms the reconnection banner at the top of every
 * attempt. Left running after the plan has given up, it takes the
 * composer back a few seconds after handing it over — so the two
 * have to agree on when the run is over.
 */
export function keepTrying({
  gaveUp,
  cancelled,
}: {
  gaveUp: boolean;
  cancelled: boolean;
}): boolean {
  return !gaveUp && !cancelled;
}
