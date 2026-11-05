import { describe, expect, it } from 'vitest';

import { presentIndexHealth } from '@/lib/index-health-view';

const healthy = {
  state: 'in-step' as const,
  missing: [] as string[],
  orphaned: [] as string[],
  failed: [] as string[],
  coverage: 1,
  trustworthy: true,
};

describe('presentIndexHealth', () => {
  it('shows nothing when the index is in step', () => {
    expect(presentIndexHealth(healthy)).toBeNull();
  });

  it('says plainly when documents are missing', () => {
    const behind = { ...healthy, state: 'behind' as const, missing: ['c'], coverage: 2 / 3, trustworthy: false };
    expect(presentIndexHealth(behind)?.headline).toBe('1 document is not searchable yet');
  });

  it('uses the plural for several missing', () => {
    const behind = {
      ...healthy,
      state: 'behind' as const,
      missing: ['b', 'c'],
      coverage: 1 / 3,
      trustworthy: false,
    };
    expect(presentIndexHealth(behind)?.headline).toBe('2 documents are not searchable yet');
  });

  it('says plainly when documents failed to index', () => {
    const broken = { ...healthy, state: 'broken' as const, failed: ['c'], trustworthy: false };
    expect(presentIndexHealth(broken)?.headline).toBe('1 document could not be indexed');
  });

  it('warns that answers may be incomplete', () => {
    const behind = { ...healthy, state: 'behind' as const, missing: ['c'], trustworthy: false };
    expect(presentIndexHealth(behind)?.warning).toBe('Answers may be missing information');
  });

  it('does not warn when only leftovers remain', () => {
    const tidy = { ...healthy, state: 'needs-tidying' as const, orphaned: ['gone'] };
    expect(presentIndexHealth(tidy)?.warning).toBe('');
  });

  it('says plainly when there is only tidying to do', () => {
    const tidy = { ...healthy, state: 'needs-tidying' as const, orphaned: ['gone'] };
    expect(presentIndexHealth(tidy)?.headline).toBe('1 removed document is still indexed');
  });

  it('shows how much of the source is searchable', () => {
    const behind = { ...healthy, state: 'behind' as const, missing: ['c'], coverage: 2 / 3, trustworthy: false };
    expect(presentIndexHealth(behind)?.coverage).toBe('67% searchable');
  });

  it('lists what is affected', () => {
    const broken = { ...healthy, state: 'broken' as const, failed: ['c'], trustworthy: false };
    expect(presentIndexHealth(broken)?.documents).toEqual(['c']);
  });

  it('offers to index what is missing', () => {
    const behind = { ...healthy, state: 'behind' as const, missing: ['c'], trustworthy: false };
    expect(presentIndexHealth(behind)?.action).toBe('index-now');
  });

  it('offers to look at what failed rather than retry blindly', () => {
    const broken = { ...healthy, state: 'broken' as const, failed: ['c'], trustworthy: false };
    expect(presentIndexHealth(broken)?.action).toBe('view-errors');
  });

  it('offers to tidy leftovers', () => {
    const tidy = { ...healthy, state: 'needs-tidying' as const, orphaned: ['gone'] };
    expect(presentIndexHealth(tidy)?.action).toBe('tidy');
  });

  it('treats failures as serious', () => {
    const broken = { ...healthy, state: 'broken' as const, failed: ['c'], trustworthy: false };
    expect(presentIndexHealth(broken)?.severity).toBe('high');
  });

  it('treats tidying as routine', () => {
    const tidy = { ...healthy, state: 'needs-tidying' as const, orphaned: ['gone'] };
    expect(presentIndexHealth(tidy)?.severity).toBe('info');
  });
});
