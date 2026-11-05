import { useCallback, useEffect, useRef, useState } from 'react';

import { runStillGoing } from '../services/run-status';

const ASK_EVERY_MS = 2000;
const GIVE_UP_AFTER_MS = 30000;

/**
 * Whether a stop that was asked for has actually landed.
 *
 * Pressing stop ends the stream the browser is reading, so the UI
 * knows at once that nothing more is coming — but the agent carries
 * on until the step in flight finishes, which can take seconds. Left
 * alone the composer flips straight back to "send", which reads as
 * "that's done" when it is not. Asking the agent is the only way to
 * know, and the clock is there so an answer that never comes cannot
 * leave the conversation saying "stopping" for ever.
 */
export function useStoppingRun(threadId: string | undefined): {
  stopping: boolean;
  stopRequested: () => void;
} {
  const [askedAt, setAskedAt] = useState<number | null>(null);
  const live = useRef(true);

  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
    };
  }, []);

  // A stop belongs to the conversation it was asked in.
  useEffect(() => setAskedAt(null), [threadId]);

  useEffect(() => {
    if (askedAt === null || !threadId) return;

    const settled = () => live.current && setAskedAt(null);
    const timer = window.setInterval(() => {
      if (Date.now() - askedAt >= GIVE_UP_AFTER_MS) {
        settled();
        return;
      }
      void runStillGoing(threadId).then((going) => {
        if (!going) settled();
      });
    }, ASK_EVERY_MS);

    return () => window.clearInterval(timer);
  }, [askedAt, threadId]);

  const stopRequested = useCallback(() => setAskedAt(Date.now()), []);

  return { stopping: askedAt !== null, stopRequested };
}
