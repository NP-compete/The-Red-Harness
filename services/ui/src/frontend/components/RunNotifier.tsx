import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { shouldAsk } from '../lib/ask-permission';
import { notifiable } from '../lib/platform';
import { useRunNotifications, type RunState } from '../hooks/useRunNotifications';

export interface PwaSettings {
  enabled: boolean;
  notifications: {
    enabled: boolean;
    platforms: string[];
    events: Record<string, boolean>;
    include_detail: boolean;
    badge: boolean;
  };
}

/**
 * Tells somebody when the run they walked away from needs them.
 *
 * Renders nothing. A question that needs real work takes tens of
 * seconds and people switch away; a run that pauses for approval is
 * stopped until they come back, and without this nothing says so —
 * the interrupt mechanism becomes a way to stall quietly.
 */
export function RunNotifier({
  pwa,
  threadId,
  threadTitle,
  state,
  watching,
  startedARun = true,
}: {
  pwa: PwaSettings | null;
  threadId: string;
  threadTitle: string;
  state: RunState;
  /** The thread on screen, which may not be this one. */
  watching: string | null;
  startedARun?: boolean;
}) {
  const { t } = useTranslation();
  const [permission, setPermission] = useState<NotificationPermission>(() =>
    typeof Notification === 'undefined' ? 'denied' : Notification.permission,
  );
  const asked = useRef(false);

  const settings = pwa?.notifications ?? null;
  const supported =
    pwa?.enabled === true &&
    settings?.enabled === true &&
    typeof Notification !== 'undefined' &&
    notifiable(
      {
        platform: (navigator as { userAgentData?: { platform?: string } }).userAgentData
          ?.platform,
        userAgent: navigator.userAgent,
      },
      settings.platforms,
    );

  useEffect(() => {
    if (!shouldAsk({ supported, permission, startedARun, alreadyAsked: asked.current })) {
      return;
    }
    asked.current = true;
    void Notification.requestPermission().then(setPermission);
  }, [supported, permission, startedARun]);

  useRunNotifications({
    threadId,
    threadTitle,
    state,
    settings: settings ?? { enabled: false, events: {}, include_detail: false },
    supported,
    permission,
    watching,
    documentVisible:
      typeof document === 'undefined' ? false : document.visibilityState === 'visible',
    show: (titleKey, body) => {
      // The keys travel this far rather than the words, so what is
      // raised is in the reader's language and not the one the run
      // happened to start in.
      new Notification(t(titleKey), {
        body: body.startsWith('notify.') ? t(body) : body,
        tag: threadId,
      });
    },
  });

  return null;
}
