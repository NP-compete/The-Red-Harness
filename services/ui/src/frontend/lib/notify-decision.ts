export type RunEventKind =
  | 'run_complete'
  | 'approval_required'
  | 'connection_required'
  | 'run_failed';

export interface RunEvent {
  kind: RunEventKind;
  threadId: string;
  threadTitle: string;
}

export interface NotificationSettings {
  enabled: boolean;
  events: Record<string, boolean>;
  /** Whether the body may carry the thread title. Off by default. */
  include_detail: boolean;
}

export interface NotificationDecision {
  notify: boolean;
  threadId: string;
  titleKey: string;
  bodyKey: string;
  body: string;
  /** The run is stopped and will stay stopped until somebody acts. */
  requiresAction: boolean;
}

/** The two that do not resume on their own. */
const NEEDS_SOMEBODY = new Set<RunEventKind>([
  'approval_required',
  'connection_required',
]);

const KNOWN = new Set<RunEventKind>([
  'run_complete',
  'approval_required',
  'connection_required',
  'run_failed',
]);

/**
 * Whether to raise a desktop notification, and what it may say.
 *
 * The interaction here is not chat: a question that needs real work
 * takes tens of seconds and people switch away. A run that pauses
 * for approval is stopped until somebody comes back to it, and
 * without this nothing says so.
 *
 * Kept separate from the raising of it so the decision can be read,
 * tested and argued with on its own.
 */
export function decideNotification({
  event,
  settings,
  supported,
  permission,
  watching,
  documentVisible,
}: {
  event: RunEvent;
  settings: NotificationSettings;
  supported: boolean;
  permission: NotificationPermission;
  /** The thread currently on screen, if any. */
  watching: string | null;
  documentVisible: boolean;
}): NotificationDecision {
  const known = KNOWN.has(event.kind);

  // Nothing about something the reader is already watching happen:
  // that trains people to dismiss without reading, and the one that
  // mattered goes with the rest.
  const alreadySeen = documentVisible && watching === event.threadId;

  const notify =
    known &&
    supported &&
    permission === 'granted' &&
    settings.enabled &&
    settings.events[event.kind] === true &&
    !alreadySeen;

  return {
    notify,
    threadId: event.threadId,
    titleKey: `notify.${event.kind}.title`,
    bodyKey: `notify.${event.kind}.body`,
    // A notification renders on a lock screen, so nothing from the
    // conversation goes in it unless a deployment said otherwise.
    body: settings.include_detail ? event.threadTitle : '',
    requiresAction: NEEDS_SOMEBODY.has(event.kind),
  };
}
