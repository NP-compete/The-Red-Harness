import { useRef } from 'react';

import { announce } from '../lib/live-region';

export interface RunReading {
  streaming: boolean;
  answerLength: number;
  needsApproval: boolean;
  failed: boolean;
}

export interface Announced {
  message: string;
  assertive: boolean;
}

/**
 * What a screen reader should hear about a run in flight.
 *
 * The finished reply is announced elsewhere and in full; this is only
 * the part a sighted reader gets from watching the text appear.
 */
const FAILED = 'Something went wrong';

export function useAnnouncer(reading: RunReading): Announced {
  const seenLength = useRef(0);
  const lastAt = useRef(0);
  const lastAnnounced = useRef('');
  const said = useRef<Announced>({ message: '', assertive: false });

  const now = Date.now();
  const startedAt = useRef(now);
  const charactersAdded = Math.max(0, reading.answerLength - seenLength.current);

  const next = announce({
    streaming: reading.streaming,
    charactersAdded,
    // Before the first announcement the quiet period runs from the
    // start of the run, so a burst in the opening instant stays quiet.
    sinceLastAnnouncementMs: now - (lastAt.current || startedAt.current),
    runFinished: false,
    needsApproval: reading.needsApproval,
    failed: reading.failed,
    lastAnnounced: lastAnnounced.current,
  });

  if (next) {
    seenLength.current = reading.answerLength;
    lastAt.current = now;
    lastAnnounced.current = next.message;
    said.current = next;
  }

  // A failure that is over must not be left standing. Everything
  // else can stay: clearing a line and putting it back is how a
  // reader hears the same thing twice, but a retry that succeeded
  // while the region still holds "Something went wrong" leaves
  // assistive technology asserting the opposite of what happened.
  if (!reading.failed && said.current.message === FAILED) {
    said.current = { message: '', assertive: false };
    lastAnnounced.current = '';
  }

  return said.current;
}
