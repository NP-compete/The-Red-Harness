import { describe, expect, it } from 'vitest';

import { presentCoverage } from '@/lib/coverage-view';

import en from '../i18n/locales/en.json';

/**
 * The module returns catalogue keys and the numbers they count: it
 * runs outside a component, where there is no translator. Resolving
 * through English keeps each assertion about the sentence a person
 * reads, and proves the key and its plural forms exist.
 */
function said(key: string, count = 0, percent?: number): string {
  if (!key) return '';
  const [section, name] = key.split('.');
  const table = (en as Record<string, Record<string, string>>)[section] ?? {};
  const form = table[`${name}_${count === 1 ? 'one' : 'other'}`] ?? table[name];
  if (form === undefined) throw new Error(`no English string for '${key}'`);
  return form
    .replace('{{count}}', String(count))
    .replace('{{percent}}', String(percent ?? ''));
}

const complete = {
  complete: true,
  uncovered: [] as string[],
  unused: [] as number[],
  share: 1,
  reason: '',
  partCount: 2,
};

describe('presentCoverage', () => {
  it('shows nothing when everything asked was found', () => {
    expect(presentCoverage(complete)).toBeNull();
  });

  it('says plainly which part went unanswered', () => {
    const partial = {
      ...complete,
      complete: false,
      uncovered: ['who approves it'],
      share: 0.5,
      reason: 'nothing found for: who approves it',
    };
    const one = presentCoverage(partial)!;
    expect(said(one.headline, one.headlineCount)).toBe('1 part of your question went unanswered');
  });

  it('uses the plural for several unanswered parts', () => {
    const partial = {
      ...complete,
      complete: false,
      uncovered: ['a', 'b'],
      share: 0.5,
      partCount: 4,
      reason: 'x',
    };
    const two = presentCoverage(partial)!;
    expect(said(two.headline, two.headlineCount)).toBe('2 parts of your question went unanswered');
  });

  it('lists the unanswered parts', () => {
    const partial = { ...complete, complete: false, uncovered: ['who approves it'], share: 0.5, reason: 'x' };
    expect(presentCoverage(partial)?.parts).toEqual(['who approves it']);
  });

  it('says plainly when nothing at all was found', () => {
    const none = {
      ...complete,
      complete: false,
      uncovered: ['a', 'b'],
      share: 0,
      reason: 'nothing was found for any part of this',
    };
    expect(said(presentCoverage(none)!.headline)).toBe('Nothing was found for your question');
  });

  it('treats finding nothing as serious', () => {
    const none = { ...complete, complete: false, uncovered: ['a', 'b'], share: 0, reason: 'x' };
    expect(presentCoverage(none)?.severity).toBe('high');
  });

  it('treats a partial answer as a caution', () => {
    const partial = { ...complete, complete: false, uncovered: ['a'], share: 0.5, reason: 'x' };
    expect(presentCoverage(partial)?.severity).toBe('medium');
  });

  it('suggests asking the missing part on its own', () => {
    const partial = { ...complete, complete: false, uncovered: ['who approves it'], share: 0.5, reason: 'x' };
    expect(presentCoverage(partial)?.action).toBe('ask-separately');
  });

  it('suggests rewording when nothing was found at all', () => {
    const none = { ...complete, complete: false, uncovered: ['a'], share: 0, reason: 'x' };
    expect(presentCoverage(none)?.action).toBe('reword');
  });

  it('mentions material that answered nothing asked', () => {
    const partial = {
      ...complete,
      complete: false,
      uncovered: ['a'],
      unused: [2, 3],
      share: 0.5,
      reason: 'x',
    };
    const spare = presentCoverage(partial)!;
    expect(said(spare.note, spare.noteCount)).toBe('2 passages were found that did not fit the question');
  });

  it('says nothing about unused material when there is none', () => {
    const partial = { ...complete, complete: false, uncovered: ['a'], share: 0.5, reason: 'x' };
    const quiet = presentCoverage(partial)!;
    expect(said(quiet.note, quiet.noteCount)).toBe('');
  });

  it('shows how much was covered', () => {
    const partial = { ...complete, complete: false, uncovered: ['a'], share: 0.5, reason: 'x' };
    const half = presentCoverage(partial)!;
    expect(said(half.covered, 0, half.coveredPercent)).toBe('50% of your question was answered');
  });
});
