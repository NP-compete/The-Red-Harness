import { render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { RunNotifier } from './RunNotifier';

const pwa = {
  enabled: true,
  notifications: {
    enabled: true,
    platforms: ['macOS', 'Windows', 'Linux'],
    events: {
      run_complete: true,
      approval_required: true,
      connection_required: true,
      run_failed: true,
    },
    include_detail: false,
    badge: true,
  },
};

let raised: { title: string; options?: NotificationOptions }[];

class FakeNotification {
  static permission: NotificationPermission = 'granted';
  static requested = 0;
  constructor(title: string, options?: NotificationOptions) {
    raised.push({ title, options });
  }
  static async requestPermission(): Promise<NotificationPermission> {
    FakeNotification.requested += 1;
    return FakeNotification.permission;
  }
  close() {}
  addEventListener() {}
}

beforeEach(() => {
  raised = [];
  FakeNotification.permission = 'granted';
  FakeNotification.requested = 0;
  vi.stubGlobal('Notification', FakeNotification);
  vi.stubGlobal('navigator', {
    ...globalThis.navigator,
    userAgentData: { platform: 'macOS' },
  });
});

afterEach(() => vi.unstubAllGlobals());

function show(over: Record<string, unknown> = {}) {
  return render(
    <RunNotifier
      pwa={pwa}
      threadId="t1"
      threadTitle="Q3 revenue"
      state="running"
      watching="t2"
      {...over}
    />,
  );
}

describe('RunNotifier', () => {
  it('renders nothing of its own', () => {
    const { container } = show();
    expect(container).toBeEmptyDOMElement();
  });

  it('raises nothing while a run is running', () => {
    show();
    expect(raised).toHaveLength(0);
  });

  it('raises one when the run stops for approval', () => {
    const { rerender } = show();
    rerender(
      <RunNotifier
        pwa={pwa}
        threadId="t1"
        threadTitle="Q3 revenue"
        state="awaiting_approval"
        watching="t2"
      />,
    );
    expect(raised).toHaveLength(1);
  });

  it('stays silent on a platform where delivery is unreliable', () => {
    vi.stubGlobal('navigator', {
      ...globalThis.navigator,
      userAgentData: { platform: 'Android' },
    });
    const { rerender } = show();
    rerender(
      <RunNotifier
        pwa={pwa}
        threadId="t1"
        threadTitle="Q3 revenue"
        state="awaiting_approval"
        watching="t2"
      />,
    );
    expect(raised).toHaveLength(0);
  });

  it('never asks for permission on an unsupported platform', () => {
    // The prompt is the damage: refused once, refused for good.
    vi.stubGlobal('navigator', {
      ...globalThis.navigator,
      userAgentData: { platform: 'iOS' },
    });
    FakeNotification.permission = 'default';
    show({ state: 'running', startedARun: true });
    expect(FakeNotification.requested).toBe(0);
  });

  it('stays silent when the deployment turned notifications off', () => {
    const quiet = { ...pwa, notifications: { ...pwa.notifications, enabled: false } };
    const { rerender } = show({ pwa: quiet });
    rerender(
      <RunNotifier
        pwa={quiet}
        threadId="t1"
        threadTitle="Q3 revenue"
        state="awaiting_approval"
        watching="t2"
      />,
    );
    expect(raised).toHaveLength(0);
  });

  it('keeps the conversation out of what it raises', () => {
    const { rerender } = show();
    rerender(
      <RunNotifier
        pwa={pwa}
        threadId="t1"
        threadTitle="Q3 revenue"
        state="awaiting_approval"
        watching="t2"
      />,
    );
    expect(JSON.stringify(raised)).not.toContain('Q3 revenue');
  });
});
