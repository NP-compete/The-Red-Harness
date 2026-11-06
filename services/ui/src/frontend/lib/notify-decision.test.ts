import { describe, expect, it } from 'vitest';

import { decideNotification, type RunEvent } from '@/lib/notify-decision';

const settings = {
  enabled: true,
  events: {
    run_complete: true,
    approval_required: true,
    connection_required: true,
    run_failed: true,
  },
  include_detail: false,
};

const event: RunEvent = {
  kind: 'approval_required',
  threadId: 't1',
  threadTitle: 'Q3 revenue by region',
};

function decide(over: Partial<Parameters<typeof decideNotification>[0]> = {}) {
  return decideNotification({
    event,
    settings,
    supported: true,
    permission: 'granted',
    watching: null,
    documentVisible: false,
    ...over,
  });
}

describe('decideNotification', () => {
  describe('the event that matters most', () => {
    it('tells somebody a run is waiting on them', () => {
      // A paused run does not resume on its own. Without this, the
      // interrupt mechanism is a way to stall quietly.
      expect(decide().notify).toBe(true);
    });

    it('names the thread it came from, so clicking can go there', () => {
      expect(decide().threadId).toBe('t1');
    });
  });

  describe('when it stays quiet', () => {
    it('on a platform where delivery is unreliable', () => {
      expect(decide({ supported: false }).notify).toBe(false);
    });

    it('when the reader has not granted permission', () => {
      expect(decide({ permission: 'default' }).notify).toBe(false);
    });

    it('when the reader has refused', () => {
      expect(decide({ permission: 'denied' }).notify).toBe(false);
    });

    it('when the deployment turned notifications off', () => {
      expect(decide({ settings: { ...settings, enabled: false } }).notify).toBe(false);
    });

    it('when the deployment turned this kind off', () => {
      const quiet = { ...settings, events: { ...settings.events, approval_required: false } };
      expect(decide({ settings: quiet }).notify).toBe(false);
    });

    it('when the reader is already watching that thread happen', () => {
      // Notifying somebody about something on their screen trains
      // them to dismiss without reading.
      expect(decide({ watching: 't1', documentVisible: true }).notify).toBe(false);
    });

    it('but not when they are watching a different thread', () => {
      expect(decide({ watching: 't2', documentVisible: true }).notify).toBe(true);
    });

    it('and not when the tab is in the background', () => {
      expect(decide({ watching: 't1', documentVisible: false }).notify).toBe(true);
    });
  });

  describe('what the notification is allowed to say', () => {
    it('says what kind of event it is', () => {
      expect(decide().titleKey).toBe('notify.approval_required.title');
    });

    it('carries no conversation content by default', () => {
      // It renders on a lock screen.
      expect(decide().body).not.toContain('Q3 revenue');
    });

    it('still says enough to act on', () => {
      expect(decide().bodyKey).toBe('notify.approval_required.body');
    });

    it('includes the thread only where a deployment opted in', () => {
      const detailed = { ...settings, include_detail: true };
      expect(decide({ settings: detailed }).body).toContain('Q3 revenue by region');
    });

    it('opting in is off by default', () => {
      expect(settings.include_detail).toBe(false);
    });
  });

  describe('the other events', () => {
    it('reports a finished run', () => {
      const done = { ...event, kind: 'run_complete' as const };
      expect(decide({ event: done }).titleKey).toBe('notify.run_complete.title');
    });

    it('reports a run waiting on a connection', () => {
      const waiting = { ...event, kind: 'connection_required' as const };
      expect(decide({ event: waiting }).notify).toBe(true);
    });

    it('reports a failure', () => {
      const failed = { ...event, kind: 'run_failed' as const };
      expect(decide({ event: failed }).notify).toBe(true);
    });

    it('says nothing about a kind it does not know', () => {
      const odd = { ...event, kind: 'something_else' as never };
      expect(decide({ event: odd }).notify).toBe(false);
    });
  });

  describe('which ones need attention rather than just informing', () => {
    it('a paused run does', () => {
      expect(decide().requiresAction).toBe(true);
    });

    it('a finished one does not', () => {
      const done = { ...event, kind: 'run_complete' as const };
      expect(decide({ event: done }).requiresAction).toBe(false);
    });
  });
});
