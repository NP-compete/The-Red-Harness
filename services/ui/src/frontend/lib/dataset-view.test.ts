import { describe, expect, it } from 'vitest';

import { presentDataset } from '@/lib/dataset-view';

const dataset = {
  count: 40,
  workingCount: 32,
  holdoutCount: 8,
  excluded: {
    'no-consent': ['a', 'b'],
    'personal-data': ['c'],
    unlabelled: [] as string[],
    duplicate: ['d'],
  },
  tooSmall: false,
};

describe('presentDataset', () => {
  it('says how many cases there are', () => {
    expect(presentDataset(dataset).headline).toBe('40 cases');
  });

  it('says how the cases are split', () => {
    expect(presentDataset(dataset).split).toBe('32 for tuning, 8 held back');
  });

  it('says plainly when nothing is held back', () => {
    const all = { ...dataset, workingCount: 40, holdoutCount: 0 };
    expect(presentDataset(all).split).toBe('40 for tuning, none held back');
  });

  it('warns when nothing is held back', () => {
    const all = { ...dataset, workingCount: 40, holdoutCount: 0 };
    expect(presentDataset(all).warning).toBe(
      'With nothing held back, improvements cannot be checked honestly',
    );
  });

  it('does not warn when a holdout exists', () => {
    expect(presentDataset(dataset).warning).toBe('');
  });

  it('explains each reason cases were left out', () => {
    expect(presentDataset(dataset).exclusions).toEqual([
      { reason: 'Nobody agreed to share these', count: 2 },
      { reason: 'These contain personal data', count: 1 },
      { reason: 'These are already in the set', count: 1 },
    ]);
  });

  it('leaves out reasons that excluded nothing', () => {
    const reasons = presentDataset(dataset).exclusions.map((item) => item.reason);
    expect(reasons).not.toContain('Nobody has labelled these');
  });

  it('counts everything left out', () => {
    expect(presentDataset(dataset).excludedCount).toBe(4);
  });

  it('warns when the set is too small to trust', () => {
    const small = { ...dataset, count: 6, workingCount: 5, holdoutCount: 1, tooSmall: true };
    expect(presentDataset(small).warning).toBe(
      'Too few cases to tell a real change from noise',
    );
  });

  it('leads with the size warning over the holdout warning', () => {
    const small = { ...dataset, count: 6, workingCount: 6, holdoutCount: 0, tooSmall: true };
    expect(presentDataset(small).warning).toBe(
      'Too few cases to tell a real change from noise',
    );
  });

  it('can be used when it is big enough and split', () => {
    expect(presentDataset(dataset).usable).toBe(true);
  });

  it('cannot be used when it is too small', () => {
    const small = { ...dataset, tooSmall: true };
    expect(presentDataset(small).usable).toBe(false);
  });

  it('suggests collecting more when it is too small', () => {
    const small = { ...dataset, tooSmall: true };
    expect(presentDataset(small).action).toBe('collect-more');
  });

  it('suggests nothing when the set is healthy', () => {
    expect(presentDataset(dataset).action).toBe('none');
  });
});
