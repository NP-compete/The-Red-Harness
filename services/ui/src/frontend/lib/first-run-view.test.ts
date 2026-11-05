import { describe, expect, it } from 'vitest';

import en from '../i18n/locales/en.json';
import { presentFirstRun } from '@/lib/first-run-view';

/**
 * The module returns catalogue keys: it runs outside a component,
 * where there is no translator. The assertions are still about what
 * a person reads, so each key is resolved through English here —
 * which also proves the key exists.
 */
function said(key: string): string {
  const [section, name] = key.split('.');
  const found = (en as Record<string, Record<string, string>>)[section]?.[name];
  if (found === undefined) throw new Error(`no English string for '${key}'`);
  return found;
}

describe('presentFirstRun', () => {
  it('shows nothing once a workspace is under way', () => {
    expect(presentFirstRun([])).toBeNull();
  });

  it('greets an empty workspace with how much is left', () => {
    expect(presentFirstRun(['connect_source', 'ask_something'])?.count).toBe(2);
  });

  it('says so when there is only one thing left', () => {
    // A count, not a sentence. The headline used to be built here by
    // appending an "s", which is a rule only English follows.
    expect(presentFirstRun(['ask_something'])?.count).toBe(1);
  });

  it('has a headline for one and for many', () => {
    expect(en.firstRun.headline_one).toContain('{{count}}');
    expect(en.firstRun.headline_other).toContain('{{count}}');
  });

  it('puts the steps in the order it was given them', () => {
    const cards = presentFirstRun(['connect_source', 'ask_something'])?.cards ?? [];
    expect(cards.map((c) => c.step)).toEqual(['connect_source', 'ask_something']);
  });

  it('gives connecting a source a title worth reading', () => {
    expect(said(presentFirstRun(['connect_source'])?.cards[0].title ?? '')).toBe('Connect a source');
  });

  it('says what connecting a source gets you', () => {
    expect(said(presentFirstRun(['connect_source'])?.cards[0].detail ?? '')).toBe(
      'Answers can draw on your own documents',
    );
  });

  it('names the button for asking a first question', () => {
    expect(said(presentFirstRun(['ask_something'])?.cards[0].action ?? '')).toBe('Ask a question');
  });

  it('gives inviting others its own card', () => {
    expect(said(presentFirstRun(['invite_others'])?.cards[0].title ?? '')).toBe('Invite your team');
  });

  it('lets every card be waved away', () => {
    const cards = presentFirstRun(['connect_source', 'ask_something'])?.cards ?? [];
    expect(cards.every((c) => c.dismissible)).toBe(true);
  });

  it('is never an interruption', () => {
    expect(presentFirstRun(['connect_source'])?.blocking).toBe(false);
  });
});
