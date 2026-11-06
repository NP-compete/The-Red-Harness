import { describe, expect, it } from 'vitest';

import { presentTitle } from '@/lib/title-suggestion-view';

const suggested = {
  text: 'Summarise the Q3 numbers',
  source: 'first-message' as const,
  pinned: false,
};

describe('presentTitle', () => {
  it('shows the suggested name', () => {
    expect(presentTitle(suggested).text).toBe('Summarise the Q3 numbers');
  });

  it('can always be renamed', () => {
    expect(presentTitle(suggested).editable).toBe(true);
  });

  it('says a name was taken from the first message', () => {
    expect(presentTitle(suggested).origin).toBe('named from your first message');
  });

  it('says a name came from an attachment', () => {
    const fromFile = { ...suggested, text: 'About report.pdf', source: 'attachment' as const };
    expect(presentTitle(fromFile).origin).toBe('named after the attached file');
  });

  it('says a placeholder is waiting for a better name', () => {
    const placeholder = { ...suggested, text: 'New conversation', source: 'placeholder' as const };
    expect(presentTitle(placeholder).origin).toBe('not named yet');
  });

  it('says nothing about origin for a name someone chose', () => {
    const chosen = { ...suggested, source: 'existing' as const, pinned: true };
    expect(presentTitle(chosen).origin).toBe('');
  });

  it('marks a chosen name so it is not overwritten', () => {
    const chosen = { ...suggested, source: 'existing' as const, pinned: true };
    expect(presentTitle(chosen).keepsOnNewMessages).toBe(true);
  });

  it('lets an automatic name be replaced later', () => {
    expect(presentTitle(suggested).keepsOnNewMessages).toBe(false);
  });

  it('marks a placeholder so the list can show it differently', () => {
    const placeholder = { ...suggested, text: 'New conversation', source: 'placeholder' as const };
    expect(presentTitle(placeholder).placeholder).toBe(true);
  });

  it('does not mark a real name as a placeholder', () => {
    expect(presentTitle(suggested).placeholder).toBe(false);
  });

  it('offers to rename a placeholder', () => {
    const placeholder = { ...suggested, text: 'New conversation', source: 'placeholder' as const };
    expect(presentTitle(placeholder).action).toBe('rename');
  });

  it('offers nothing on a name someone already chose', () => {
    const chosen = { ...suggested, source: 'existing' as const, pinned: true };
    expect(presentTitle(chosen).action).toBe('none');
  });

  it('never shows an empty name in a list', () => {
    const blank = { ...suggested, text: '   ', source: 'placeholder' as const };
    expect(presentTitle(blank).text).toBe('Untitled');
  });
});
