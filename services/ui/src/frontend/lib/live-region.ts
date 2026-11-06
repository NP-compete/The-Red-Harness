export interface AnnouncementState {
  streaming: boolean;
  charactersAdded: number;
  sinceLastAnnouncementMs: number;
  runFinished: boolean;
  needsApproval: boolean;
  failed: boolean;
  lastAnnounced: string;
}

export interface Announcement {
  message: string;
  assertive: boolean;
}

const ENOUGH_CHARACTERS = 200;
const QUIET_PERIOD_MS = 3000;

export function announce(state: AnnouncementState): Announcement | null {
  // Anything needing a person interrupts; progress never does.
  if (state.failed) return once(state, 'Something went wrong', true);
  if (state.needsApproval) return once(state, 'Waiting for your approval', true);
  if (state.runFinished) return once(state, 'Reply finished', false, { always: true });

  const worthSaying =
    // Only while it is actually still arriving. A render after the
    // stream stops can still carry a large `charactersAdded`, and
    // completion is announced by another region — so without this
    // the reader hears the reply is finished and then that it is
    // still being written.
    state.streaming &&
    state.charactersAdded >= ENOUGH_CHARACTERS &&
    state.sinceLastAnnouncementMs >= QUIET_PERIOD_MS;

  // The reply itself is readable on demand; this only reports what changed,
  // so a long answer does not become a long announcement.
  return worthSaying ? once(state, 'Still writing', false) : null;
}

function once(
  state: AnnouncementState,
  message: string,
  assertive: boolean,
  options: { always?: boolean } = {},
): Announcement | null {
  if (!options.always && state.lastAnnounced === message) return null;
  return { message, assertive };
}
