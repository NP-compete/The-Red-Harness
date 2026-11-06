import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useRunNotifications } from './useRunNotifications';

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

function raise(over: Record<string, unknown> = {}) {
  const raised: { title: string; body: string }[] = [];
  const show = (title: string, body: string) => raised.push({ title, body });
  const { rerender } = renderHook(
    (props: Record<string, unknown>) =>
      useRunNotifications({
        threadId: 't1',
        threadTitle: 'Q3 revenue',
        settings,
        supported: true,
        permission: 'granted' as NotificationPermission,
        watching: null,
        documentVisible: false,
        show,
        state: 'running',
        ...props,
      }),
    { initialProps: { ...over } },
  );
  return { raised, rerender };
}

describe('useRunNotifications', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('says nothing while a run is simply running', () => {
    const { raised } = raise();
    expect(raised).toHaveLength(0);
  });

  it('speaks when the run stops for approval', () => {
    const { raised, rerender } = raise();
    rerender({ state: 'awaiting_approval' });
    expect(raised).toHaveLength(1);
  });

  it('says which kind of event it was', () => {
    const { raised, rerender } = raise();
    rerender({ state: 'awaiting_approval' });
    expect(raised[0].title).toBe('notify.approval_required.title');
  });

  it('speaks once, not on every render', () => {
    // The hook runs on every state change; a notification per render
    // is how a useful alert becomes something people switch off.
    const { raised, rerender } = raise();
    rerender({ state: 'awaiting_approval' });
    rerender({ state: 'awaiting_approval' });
    rerender({ state: 'awaiting_approval' });
    expect(raised).toHaveLength(1);
  });

  it('speaks again when the run stops a second time', () => {
    const { raised, rerender } = raise();
    rerender({ state: 'awaiting_approval' });
    rerender({ state: 'running' });
    rerender({ state: 'awaiting_approval' });
    expect(raised).toHaveLength(2);
  });

  it('speaks when the run finishes', () => {
    const { raised, rerender } = raise();
    rerender({ state: 'done' });
    expect(raised[0].title).toBe('notify.run_complete.title');
  });

  it('stays quiet about a thread the reader is watching', () => {
    const { raised, rerender } = raise({ watching: 't1', documentVisible: true });
    rerender({ state: 'awaiting_approval', watching: 't1', documentVisible: true });
    expect(raised).toHaveLength(0);
  });

  it('stays quiet on a platform where delivery is unreliable', () => {
    const { raised, rerender } = raise({ supported: false });
    rerender({ state: 'awaiting_approval', supported: false });
    expect(raised).toHaveLength(0);
  });

  it('carries no conversation content by default', () => {
    const { raised, rerender } = raise();
    rerender({ state: 'awaiting_approval' });
    expect(raised[0].body).not.toContain('Q3 revenue');
  });
});
