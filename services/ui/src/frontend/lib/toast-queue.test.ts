import { describe, expect, it } from 'vitest';

import { queueToasts } from '@/lib/toast-queue';

const now = new Date('2026-10-27T09:00:00Z');

const toast = (id: string, overrides = {}) => ({
  id,
  message: `message ${id}`,
  severity: 'info' as const,
  at: '2026-10-27T09:00:00Z',
  dismissed: false,
  ...overrides,
});

describe('queueToasts', () => {
  it('shows a single message', () => {
    expect(queueToasts([toast('a')], now).visible.map((t) => t.id)).toEqual(['a']);
  });

  it('shows the newest first', () => {
    const older = toast('a', { at: '2026-10-27T08:00:00Z' });
    expect(queueToasts([older, toast('b')], now).visible[0].id).toBe('b');
  });

  it('shows no more than three at once', () => {
    const many = ['a', 'b', 'c', 'd', 'e'].map((id) => toast(id));
    expect(queueToasts(many, now).visible).toHaveLength(3);
  });

  it('says how many are waiting behind', () => {
    const many = ['a', 'b', 'c', 'd', 'e'].map((id) => toast(id));
    expect(queueToasts(many, now).hidden).toBe(2);
  });

  it('never hides an error behind ordinary messages', () => {
    const many = [
      toast('a'),
      toast('b'),
      toast('c'),
      toast('urgent', { severity: 'error' as const, at: '2026-10-27T08:00:00Z' }),
    ];
    expect(queueToasts(many, now).visible.map((t) => t.id)).toContain('urgent');
  });

  it('collapses repeats of the same message', () => {
    const repeated = [toast('a'), toast('b', { message: 'message a' })];
    expect(queueToasts(repeated, now).visible).toHaveLength(1);
  });

  it('says how many times a repeated message happened', () => {
    const repeated = [toast('a'), toast('b', { message: 'message a' })];
    expect(queueToasts(repeated, now).visible[0].repeats).toBe(2);
  });

  it('does not mark a one-off message as repeated', () => {
    expect(queueToasts([toast('a')], now).visible[0].repeats).toBe(1);
  });

  it('dismisses an ordinary message by itself', () => {
    expect(queueToasts([toast('a')], now).visible[0].autoDismissMs).toBe(5000);
  });

  it('leaves an error on screen until it is dismissed', () => {
    const error = toast('a', { severity: 'error' as const });
    expect(queueToasts([error], now).visible[0].autoDismissMs).toBeNull();
  });

  it('gives a warning longer than an ordinary message', () => {
    const warning = toast('a', { severity: 'warning' as const });
    expect(queueToasts([warning], now).visible[0].autoDismissMs).toBe(10000);
  });

  it('drops anything already dismissed', () => {
    const gone = toast('a', { dismissed: true });
    expect(queueToasts([gone, toast('b')], now).visible.map((t) => t.id)).toEqual(['b']);
  });

  it('shows nothing when everything has been dismissed', () => {
    const gone = toast('a', { dismissed: true });
    expect(queueToasts([gone], now).visible).toEqual([]);
  });

  it('reports nothing waiting when everything fits', () => {
    expect(queueToasts([toast('a')], now).hidden).toBe(0);
  });
});
