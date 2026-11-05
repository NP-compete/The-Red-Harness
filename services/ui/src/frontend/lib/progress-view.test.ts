import { describe, expect, it } from 'vitest';

import { presentProgress } from '@/lib/progress-view';

import en from '../i18n/locales/en.json';
import type { Phrase } from './progress-view';

/**
 * The module returns catalogue keys and the values they interpolate:
 * it runs outside a component, where there is no translator.
 * Resolving through English keeps each assertion about the sentence
 * a person reads, and proves the key and its plural forms exist.
 */
function said(phrase: Phrase | null): string {
  if (phrase === null) return '';
  const [section, name] = phrase.key.split('.');
  const table = (en as Record<string, Record<string, string>>)[section] ?? {};
  const count = phrase.count;
  const form =
    count === undefined
      ? table[name]
      : table[`${name}_${count === 1 ? 'one' : 'other'}`] ?? table[name];
  if (form === undefined) throw new Error(`no English string for '${phrase.key}'`);
  let out = form.replace('{{count}}', String(count ?? ''));
  for (const [key, value] of Object.entries(phrase.values ?? {})) {
    out = out.replace(`{{${key}}}`, String(value));
  }
  return out;
}

const progress = {
  doing: 'write the summary',
  done: 2,
  total: 3,
  fraction: 2 / 3,
  remainingSeconds: 30,
  elapsedSeconds: 60,
  totalIsFinal: true,
  overrunning: false,
};

describe('presentProgress', () => {
  it('says what is happening now', () => {
    expect(presentProgress(progress).doing).toBe('Write the summary');
  });

  it('says how far along it is', () => {
    expect(said(presentProgress(progress).steps)).toBe('step 3 of 3');
  });

  it('says how much longer it should take', () => {
    expect(said(presentProgress(progress).remaining)).toBe('about 30 seconds left');
  });

  it('rounds a longer estimate to minutes', () => {
    expect(said(presentProgress({ ...progress, remainingSeconds: 200 }).remaining)).toBe(
      'about 3 minutes left',
    );
  });

  it('gives a bar position when the total is known', () => {
    expect(presentProgress(progress).bar).toBeCloseTo(0.667, 2);
  });

  it('gives no bar when the number of steps may grow', () => {
    const open = { ...progress, fraction: null, remainingSeconds: null, totalIsFinal: false };
    expect(presentProgress(open).bar).toBeNull();
  });

  it('counts steps without implying an end when more may appear', () => {
    const open = { ...progress, fraction: null, remainingSeconds: null, totalIsFinal: false };
    expect(said(presentProgress(open).steps)).toBe('3 steps so far');
  });

  it('says nothing about time left rather than guessing', () => {
    const open = { ...progress, fraction: null, remainingSeconds: null, totalIsFinal: false };
    expect(said(presentProgress(open).remaining)).toBe('');
  });

  it('says how long it has been going', () => {
    expect(said(presentProgress(progress).elapsed)).toBe('1 minute');
  });

  it('flags a run taking much longer than expected', () => {
    const slow = { ...progress, overrunning: true, elapsedSeconds: 7200 };
    expect(said(presentProgress(slow).note)).toBe('This is taking longer than usual');
  });

  it('adds no note to a run going to plan', () => {
    expect(said(presentProgress(progress).note)).toBe('');
  });

  it('says plainly when the work has finished', () => {
    // The word is the catalogue's; what the module says is that
    // there is nothing in progress any more.
    const done = { ...progress, doing: '', done: 3, fraction: 1, remainingSeconds: 0 };
    expect(presentProgress(done).finished).toBe(true);
    expect(presentProgress(done).doing).toBe('');
    expect(en.progress.finished).toBe('Finished');
  });

  it('shows a finished run as complete', () => {
    const done = { ...progress, doing: '', done: 3, fraction: 1, remainingSeconds: 0 };
    expect(presentProgress(done).bar).toBe(1);
  });

  it('offers no time left once it has finished', () => {
    const done = { ...progress, doing: '', done: 3, fraction: 1, remainingSeconds: 0 };
    expect(said(presentProgress(done).remaining)).toBe('');
  });
});
