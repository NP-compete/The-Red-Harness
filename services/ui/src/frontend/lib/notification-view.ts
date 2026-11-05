export interface Notification {
  id: string;
  kind: string;
  title: string;
  at: string;
  urgency: 'normal' | 'urgent';
  read: boolean;
  runId: string;
}

export interface NotificationRow extends Notification {
  when: string;
  actionable: boolean;
  repeats: number;
}

export interface PresentedNotifications {
  items: NotificationRow[];
  unread: number;
  emptyMessage: string;
}

const ACTIONABLE = new Set(['approval-needed', 'input-needed', 'budget-exceeded']);

export function presentNotifications(
  notifications: Notification[],
  now: Date,
): PresentedNotifications {
  const groups = new Map<string, Notification[]>();
  for (const notification of notifications) {
    const key = `${notification.runId}\u001f${notification.kind}`;
    groups.set(key, [...(groups.get(key) ?? []), notification]);
  }

  const items = [...groups.values()]
    .map((group) => {
      const [newest] = [...group].sort((a, b) => Date.parse(b.at) - Date.parse(a.at));
      return {
        ...newest,
        when: ago(newest.at, now),
        actionable: ACTIONABLE.has(newest.kind),
        repeats: group.length,
      };
    })
    .sort(
      (a, b) =>
        Number(a.read) - Number(b.read) ||
        rank(b.urgency) - rank(a.urgency) ||
        Date.parse(b.at) - Date.parse(a.at),
    );

  return {
    items,
    unread: items.filter((item) => !item.read).length,
    emptyMessage: items.length === 0 ? 'Nothing needs your attention' : '',
  };
}

function rank(urgency: Notification['urgency']): number {
  return urgency === 'urgent' ? 1 : 0;
}

function ago(at: string, now: Date): string {
  const minutes = Math.round((now.getTime() - Date.parse(at)) / 60_000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}
