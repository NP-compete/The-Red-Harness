import { describe, expect, it } from 'vitest';

import { resolveSelection } from '@/lib/bulk-select';

const page = ['a', 'b', 'c'];

const empty = { mode: 'none' as const, picked: [] as string[], excluded: [] as string[] };

describe('resolveSelection', () => {
  it('starts with nothing selected', () => {
    expect(resolveSelection(empty, { page, total: 10 }).count).toBe(0);
  });

  it('counts individually picked items', () => {
    const picked = { ...empty, mode: 'some' as const, picked: ['a', 'c'] };
    expect(resolveSelection(picked, { page, total: 10 }).count).toBe(2);
  });

  it('knows which items on this page are selected', () => {
    const picked = { ...empty, mode: 'some' as const, picked: ['a', 'c'] };
    const shown = resolveSelection(picked, { page, total: 10 });
    expect(shown.isSelected('a')).toBe(true);
    expect(shown.isSelected('b')).toBe(false);
  });

  it('counts everything when all are selected', () => {
    const all = { ...empty, mode: 'all' as const };
    expect(resolveSelection(all, { page, total: 10 }).count).toBe(10);
  });

  it('treats everything as selected when all are selected', () => {
    const all = { ...empty, mode: 'all' as const };
    expect(resolveSelection(all, { page, total: 10 }).isSelected('z')).toBe(true);
  });

  it('subtracts items excluded from a select-all', () => {
    const all = { ...empty, mode: 'all' as const, excluded: ['b'] };
    expect(resolveSelection(all, { page, total: 10 }).count).toBe(9);
  });

  it('does not treat an excluded item as selected', () => {
    const all = { ...empty, mode: 'all' as const, excluded: ['b'] };
    expect(resolveSelection(all, { page, total: 10 }).isSelected('b')).toBe(false);
  });

  it('describes a select-all plainly', () => {
    const all = { ...empty, mode: 'all' as const };
    expect(resolveSelection(all, { page, total: 10 }).summary).toBe('All 10 selected');
  });

  it('describes a select-all with exceptions', () => {
    const all = { ...empty, mode: 'all' as const, excluded: ['b', 'c'] };
    expect(resolveSelection(all, { page, total: 10 }).summary).toBe('8 of 10 selected');
  });

  it('describes an ordinary selection', () => {
    const picked = { ...empty, mode: 'some' as const, picked: ['a'] };
    expect(resolveSelection(picked, { page, total: 10 }).summary).toBe('1 selected');
  });

  it('says plainly when nothing is selected', () => {
    expect(resolveSelection(empty, { page, total: 10 }).summary).toBe('Nothing selected');
  });

  it('says whether the selection reaches beyond this page', () => {
    const all = { ...empty, mode: 'all' as const };
    expect(resolveSelection(all, { page, total: 10 }).beyondThisPage).toBe(true);
  });

  it('says a picked selection does not reach beyond this page', () => {
    const picked = { ...empty, mode: 'some' as const, picked: ['a'] };
    expect(resolveSelection(picked, { page, total: 10 }).beyondThisPage).toBe(false);
  });

  it('knows when every item on the page is selected', () => {
    const picked = { ...empty, mode: 'some' as const, picked: ['a', 'b', 'c'] };
    expect(resolveSelection(picked, { page, total: 10 }).pageFullySelected).toBe(true);
  });

  it('never reports more selected than exist', () => {
    const all = { ...empty, mode: 'all' as const, excluded: ['a', 'b', 'c'] };
    expect(resolveSelection(all, { page, total: 2 }).count).toBe(0);
  });
});
