import { describe, expect, it } from 'vitest';

import { presentStall } from '@/lib/stall-view';

import en from '../i18n/locales/en.json';

/**
 * The module returns catalogue keys plus the numbers and names they
 * interpolate: it runs outside a component, where there is no
 * translator. Resolving through English here keeps each assertion
 * about what a person reads, and proves the key exists.
 */
function said(key: string, count: number, tool = ''): string {
  const [section, name] = key.split('.');
  const table = (en as Record<string, Record<string, string>>)[section] ?? {};
  const form = table[`${name}_${count === 1 ? 'one' : 'other'}`] ?? table[name];
  if (form === undefined) throw new Error(`no English string for '${key}'`);
  return form.replace('{{count}}', String(count)).replace('{{tool}}', tool);
}

const working = {
  state: 'working' as const,
  quietForSeconds: 5,
  needsAttention: false,
  reason: '',
  toolRunning: '',
};

describe('presentStall', () => {
  it('shows nothing while a run is working', () => {
    expect(presentStall(working)).toBeNull();
  });

  it('shows nothing while a run waits on a person', () => {
    const waiting = { ...working, state: 'waiting' as const, quietForSeconds: 7200 };
    expect(presentStall(waiting)).toBeNull();
  });

  it('says plainly when a run has gone quiet', () => {
    const quiet = {
      ...working,
      state: 'stalled' as const,
      quietForSeconds: 300,
      needsAttention: true,
      reason: 'nothing has happened for 300s',
    };
    const q = presentStall(quiet)!;
    expect(said(q.headline, q.headlineCount)).toBe('Nothing has happened for 5 minutes');
  });

  it('names a tool that is taking too long', () => {
    const hung = {
      ...working,
      state: 'tool-hung' as const,
      quietForSeconds: 300,
      needsAttention: true,
      toolRunning: 'search',
      reason: 'search has been running for 300s',
    };
    const h = presentStall(hung)!;
    expect(said(h.headline, h.headlineCount, h.tool)).toBe('search is taking longer than expected');
  });

  it('counts a short silence in seconds', () => {
    const quiet = {
      ...working,
      state: 'stalled' as const,
      quietForSeconds: 45,
      needsAttention: true,
      reason: 'x',
    };
    const q = presentStall(quiet)!;
    expect(said(q.headline, q.headlineCount)).toBe('Nothing has happened for 45 seconds');
  });

  it('offers to stop a stalled run', () => {
    const quiet = { ...working, state: 'stalled' as const, needsAttention: true, reason: 'x' };
    expect(presentStall(quiet)?.action).toBe('stop');
  });

  it('offers to stop a hung tool too', () => {
    const hung = {
      ...working,
      state: 'tool-hung' as const,
      needsAttention: true,
      toolRunning: 'search',
      reason: 'x',
    };
    expect(presentStall(hung)?.action).toBe('stop');
  });

  it('warns that stopping may leave a step half done', () => {
    const hung = {
      ...working,
      state: 'tool-hung' as const,
      needsAttention: true,
      toolRunning: 'search',
      reason: 'x',
    };
    const h = presentStall(hung)!;
    expect(said(h.note, 0, h.tool)).toBe('search will finish before the run stops');
  });

  it('has no such note when no tool is running', () => {
    const quiet = { ...working, state: 'stalled' as const, needsAttention: true, reason: 'x' };
    expect(presentStall(quiet)?.note).toBe('');
  });

  it('never says the run has failed', () => {
    const quiet = { ...working, state: 'stalled' as const, needsAttention: true, reason: 'x' };
    expect(presentStall(quiet)?.failed).toBe(false);
  });

  it('treats a stall as worth noticing', () => {
    const quiet = { ...working, state: 'stalled' as const, needsAttention: true, reason: 'x' };
    expect(presentStall(quiet)?.severity).toBe('medium');
  });

  it('keeps the detail for anyone who wants it', () => {
    const quiet = {
      ...working,
      state: 'stalled' as const,
      needsAttention: true,
      reason: 'nothing has happened for 300s',
    };
    expect(presentStall(quiet)?.detail).toBe('nothing has happened for 300s');
  });
});
