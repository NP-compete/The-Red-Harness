import { describe, expect, it } from 'vitest';

import { presentNotifications } from '@/lib/notification-view';

const now = new Date('2026-10-27T09:00:00Z');

const notifications = [
  {
    id: 'n1',
    kind: 'approval-needed',
    title: 'Deploy needs your approval',
    at: '2026-10-27T08:58:00Z',
    urgency: 'urgent' as const,
    read: false,
    runId: 'run-1',
  },
  {
    id: 'n2',
    kind: 'run-finished',
    title: 'Nightly digest finished',
    at: '2026-10-27T07:00:00Z',
    urgency: 'normal' as const,
    read: true,
    runId: 'run-2',
  },
];

describe('presentNotifications', () => {
  it('puts unread before read', () => {
    const shown = presentNotifications([notifications[1], notifications[0]], now);
    expect(shown.items.map((item) => item.id)).toEqual(['n1', 'n2']);
  });

  it('puts urgent before ordinary when both are unread', () => {
    const extra = { ...notifications[1], id: 'n3', read: false, at: '2026-10-27T08:59:00Z' };
    const shown = presentNotifications([extra, notifications[0]], now);
    expect(shown.items.map((item) => item.id)).toEqual(['n1', 'n3']);
  });

  it('says how long ago each arrived', () => {
    expect(presentNotifications(notifications, now).items[0].when).toBe('2 minutes ago');
  });

  it('counts the unread ones', () => {
    expect(presentNotifications(notifications, now).unread).toBe(1);
  });

  it('says which ones still need the person to do something', () => {
    expect(presentNotifications(notifications, now).items[0].actionable).toBe(true);
  });

  it('does not ask for action on something already finished', () => {
    expect(presentNotifications(notifications, now).items[1].actionable).toBe(false);
  });

  it('groups repeats of the same run into one line', () => {
    const repeats = [
      notifications[0],
      { ...notifications[0], id: 'n4', at: '2026-10-27T08:50:00Z' },
      { ...notifications[0], id: 'n5', at: '2026-10-27T08:40:00Z' },
    ];
    expect(presentNotifications(repeats, now).items).toHaveLength(1);
  });

  it('says how many were folded into the line', () => {
    const repeats = [
      notifications[0],
      { ...notifications[0], id: 'n4', at: '2026-10-27T08:50:00Z' },
    ];
    expect(presentNotifications(repeats, now).items[0].repeats).toBe(2);
  });

  it('keeps the most recent of a group', () => {
    const repeats = [
      { ...notifications[0], id: 'n4', at: '2026-10-27T08:50:00Z' },
      notifications[0],
    ];
    expect(presentNotifications(repeats, now).items[0].id).toBe('n1');
  });

  it('does not group different runs together', () => {
    expect(presentNotifications(notifications, now).items).toHaveLength(2);
  });

  it('says plainly when there is nothing waiting', () => {
    const shown = presentNotifications([], now);
    expect(shown.items).toEqual([]);
    expect(shown.emptyMessage).toBe('Nothing needs your attention');
  });

  it('has no empty message when there is something', () => {
    expect(presentNotifications(notifications, now).emptyMessage).toBe('');
  });
});
