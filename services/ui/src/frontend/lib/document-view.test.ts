import { describe, expect, it } from 'vitest';

import { describeLibrary, formatBytes } from './document-view';

const REPORT = {
  documents: [
    { id: 'user:1', title: 'Notes', bytes: 2048 },
    { id: 'user:2', title: 'Handbook', bytes: 1024 },
  ],
  used_bytes: 3072,
  limit_bytes: 10240,
};

describe('formatBytes', () => {
  it('reads bytes as bytes when they are small', () => {
    expect(formatBytes(512)).toBe('512 B');
  });

  it('reads larger sizes in kilobytes', () => {
    expect(formatBytes(2048)).toBe('2.0 KB');
  });

  it('reads larger ones still in megabytes', () => {
    expect(formatBytes(5 * 1024 * 1024)).toBe('5.0 MB');
  });

  it('reads nothing as nothing rather than as 0.0 KB', () => {
    expect(formatBytes(0)).toBe('0 B');
  });
});

describe('describeLibrary', () => {
  it('lists what is there', () => {
    expect(describeLibrary(REPORT)?.documents).toHaveLength(2);
  });

  it('gives each a readable size', () => {
    expect(describeLibrary(REPORT)?.documents[0].size).toBe('2.0 KB');
  });

  it('says how full it is', () => {
    expect(describeLibrary(REPORT)?.usedLabel).toBe('3.0 KB');
  });

  it('says what the limit is', () => {
    expect(describeLibrary(REPORT)?.limitLabel).toBe('10.0 KB');
  });

  it('works out how full as a fraction', () => {
    expect(describeLibrary(REPORT)?.fraction).toBeCloseTo(0.3);
  });

  describe('when it is nearly full', () => {
    it('says so', () => {
      // Somebody about to be refused should see it coming
      // rather than find out by being refused.
      const full = { ...REPORT, used_bytes: 9728 };
      expect(describeLibrary(full)?.nearlyFull).toBe(true);
    });

    it('does not say so with room to spare', () => {
      expect(describeLibrary(REPORT)?.nearlyFull).toBe(false);
    });
  });

  describe('a quota of nothing', () => {
    it('does not divide by zero', () => {
      // A deployment that keeps a corpus and no personal
      // uploads. The page should say full, not NaN.
      const closed = { documents: [], used_bytes: 0, limit_bytes: 0 };
      expect(describeLibrary(closed)?.fraction).toBe(1);
    });

    it('is reported as full', () => {
      const closed = { documents: [], used_bytes: 0, limit_bytes: 0 };
      expect(describeLibrary(closed)?.nearlyFull).toBe(true);
    });
  });

  describe('an agent that does not offer this', () => {
    it('reports nothing rather than an empty library', () => {
      // "No documents" and "no such page" are different, and
      // the first invites somebody to add one.
      expect(describeLibrary(null)).toBe(null);
    });
  });
});

describe('what a team shares', () => {
  const WITH_TEAM = {
    documents: [{ id: 'user:1', title: 'Notes', bytes: 2048 }],
    team: [
      { id: 'corpus:teams/platform/runbook.md', title: 'runbook', bytes: 512, team: 'platform' },
    ],
    used_bytes: 2048,
    limit_bytes: 10240,
  };

  it('lists them', () => {
    expect(describeLibrary(WITH_TEAM)?.shared).toHaveLength(1);
  });

  it('says which team each came from', () => {
    // "Who else can see this" is the question somebody has.
    expect(describeLibrary(WITH_TEAM)?.shared[0].team).toBe('platform');
  });

  it('keeps them out of the personal list', () => {
    expect(describeLibrary(WITH_TEAM)?.documents).toHaveLength(1);
  });

  it('gives each a readable size', () => {
    expect(describeLibrary(WITH_TEAM)?.shared[0].size).toBe('512 B');
  });

  it('reports none when the agent sent no team block', () => {
    // An older agent that never answers this is not a person
    // with no teams — but it looks the same here, and empty is
    // the safe reading either way.
    const without = { documents: [], used_bytes: 0, limit_bytes: 10240 };
    expect(describeLibrary(without)?.shared).toEqual([]);
  });
});
