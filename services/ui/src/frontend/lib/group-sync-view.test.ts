import { describe, expect, it } from 'vitest';

import { presentSyncResults } from '@/lib/group-sync-view';

const results = [
  {
    person: 'ana',
    teams: ['engineering'],
    roles: [],
    unmapped: [],
    changed: false,
    removedAll: false,
    reason: '',
  },
  {
    person: 'bo',
    teams: [],
    roles: [],
    unmapped: ['social-club'],
    changed: true,
    removedAll: true,
    reason: '',
  },
  {
    person: 'cy',
    teams: ['finance'],
    roles: ['approver'],
    unmapped: [],
    changed: true,
    removedAll: false,
    reason: '',
  },
];

describe('presentSyncResults', () => {
  it('shows only the people whose access changed', () => {
    expect(presentSyncResults(results).rows.map((row) => row.person)).toEqual(['bo', 'cy']);
  });

  it('puts people losing all access first', () => {
    expect(presentSyncResults(results).rows[0].person).toBe('bo');
  });

  it('says plainly when someone lost everything', () => {
    expect(presentSyncResults(results).rows[0].summary).toBe('loses all access');
  });

  it('says what someone gained', () => {
    expect(presentSyncResults(results).rows[1].summary).toBe('finance, approver');
  });

  it('marks a total loss as needing a second look', () => {
    expect(presentSyncResults(results).rows[0].attention).toBe(true);
  });

  it('does not mark an ordinary change', () => {
    expect(presentSyncResults(results).rows[1].attention).toBe(false);
  });

  it('counts how many people are affected', () => {
    expect(presentSyncResults(results).changedCount).toBe(2);
  });

  it('collects groups that map to nothing', () => {
    expect(presentSyncResults(results).unmappedGroups).toEqual(['social-club']);
  });

  it('does not repeat an unmapped group seen for several people', () => {
    const shared = [
      { ...results[1], person: 'bo' },
      { ...results[1], person: 'dee' },
    ];
    expect(presentSyncResults(shared).unmappedGroups).toEqual(['social-club']);
  });

  it('surfaces people the sync skipped rather than hiding them', () => {
    const stale = [
      { ...results[0], person: 'eli', reason: 'this view of the directory is stale' },
    ];
    expect(presentSyncResults(stale).skipped).toEqual(['eli']);
  });

  it('does not count a skipped person as changed', () => {
    const stale = [
      { ...results[0], person: 'eli', changed: true, reason: 'this view is stale' },
    ];
    expect(presentSyncResults(stale).changedCount).toBe(0);
  });

  it('says plainly when nothing changed at all', () => {
    expect(presentSyncResults([results[0]]).emptyMessage).toBe('No access changes');
  });

  it('has no empty message when something changed', () => {
    expect(presentSyncResults(results).emptyMessage).toBe('');
  });
});
