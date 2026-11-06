import { describe, expect, it } from 'vitest';

import { presentMemory } from '@/lib/memory-view';

const fact = {
  text: 'prefers short answers',
  sourceThread: 't1',
  sourceTitle: 'Quarterly review',
  notedAt: '2026-10-20',
};

describe('presentMemory', () => {
  it('shows what is remembered', () => {
    expect(presentMemory([fact]).rows[0].text).toBe('prefers short answers');
  });

  it('shows where it was learned, so it can be checked', () => {
    expect(presentMemory([fact]).rows[0].source).toBe('Quarterly review');
  });

  it('falls back to the conversation reference when there is no title', () => {
    const rows = presentMemory([{ ...fact, sourceTitle: undefined }]).rows;
    expect(rows[0].source).toBe('t1');
  });

  it('offers to forget every fact', () => {
    expect(presentMemory([fact]).rows[0].actions).toEqual(['forget']);
  });

  it('puts the most recent first', () => {
    const rows = presentMemory([
      { ...fact, text: 'older', notedAt: '2026-01-01' },
      { ...fact, text: 'newer', notedAt: '2026-10-20' },
    ]).rows;
    expect(rows.map((row) => row.text)).toEqual(['newer', 'older']);
  });

  it('says plainly when nothing is remembered', () => {
    const shown = presentMemory([]);
    expect(shown.rows).toEqual([]);
    expect(shown.emptyMessage).toBeTruthy();
  });

  it('explains that remembering is off until something is learned', () => {
    expect(presentMemory([]).emptyMessage.toLowerCase()).toContain('nothing');
  });

  it('counts what is held', () => {
    expect(presentMemory([fact, { ...fact, text: 'another' }]).count).toBe(2);
  });

  it('offers to forget everything at once when there is something to forget', () => {
    expect(presentMemory([fact]).bulkAction).toBe('forget-all');
  });

  it('offers no bulk action when there is nothing held', () => {
    expect(presentMemory([]).bulkAction).toBeUndefined();
  });
});
