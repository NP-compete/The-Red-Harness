import { useEffect, useRef } from 'react';

import {
  decideNotification,
  type NotificationSettings,
  type RunEventKind,
} from '../lib/notify-decision';

export type RunState =
  | 'running'
  | 'awaiting_approval'
  | 'awaiting_connection'
  | 'done'
  | 'failed';

/** The run states worth telling somebody about, and what they are called. */
const WORTH_SAYING: Partial<Record<RunState, RunEventKind>> = {
  awaiting_approval: 'approval_required',
  awaiting_connection: 'connection_required',
  done: 'run_complete',
  failed: 'run_failed',
};

/**
 * Tell somebody when the run they started needs them, or is done.
 *
 * Only on the edge into a state, never while sitting in one. A
 * notification per render is how a useful alert becomes the thing
 * people switch off, and then the one that mattered goes with it.
 */
export function useRunNotifications({
  threadId,
  threadTitle,
  state,
  settings,
  supported,
  permission,
  watching,
  documentVisible,
  show,
}: {
  threadId: string;
  threadTitle: string;
  state: RunState;
  settings: NotificationSettings;
  supported: boolean;
  permission: NotificationPermission;
  watching: string | null;
  documentVisible: boolean;
  show: (title: string, body: string) => void;
}) {
  const previous = useRef<RunState | null>(null);

  useEffect(() => {
    const was = previous.current;
    previous.current = state;
    if (was === state) return;

    const kind = WORTH_SAYING[state];
    if (!kind) return;

    const decided = decideNotification({
      event: { kind, threadId, threadTitle },
      settings,
      supported,
      permission,
      watching,
      documentVisible,
    });
    if (decided.notify) {
      show(decided.titleKey, decided.body || decided.bodyKey);
    }
    // `show` and `settings` are deliberately absent: a new function
    // identity or a re-read config should not re-announce something
    // that already happened.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, threadId, supported, permission, watching, documentVisible]);
}
