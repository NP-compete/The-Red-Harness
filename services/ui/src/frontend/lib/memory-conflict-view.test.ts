import { describe, expect, it } from 'vitest';

import { presentMemoryChange } from '@/lib/memory-conflict-view';

const change = {
  key: 'preferred-format',
  label: 'Preferred format',
  resolution: 'superseded' as const,
  keptValue: 'plain text',
  replacedValue: 'markdown',
  source: 'stated' as const,
  worthMentioning: true,
};

describe('presentMemoryChange', () => {
  it('shows nothing for a change not worth mentioning', () => {
    const quiet = { ...change, resolution: 'added' as const, worthMentioning: false };
    expect(presentMemoryChange(quiet)).toBeNull();
  });

  it('says plainly what it now remembers', () => {
    expect(presentMemoryChange(change)?.headline).toBe(
      'Preferred format is now plain text, not markdown',
    );
  });

  it('says when it kept what it had instead', () => {
    const kept = {
      ...change,
      resolution: 'kept-existing' as const,
      keptValue: 'markdown',
      replacedValue: '',
      source: 'inferred' as const,
    };
    expect(presentMemoryChange(kept)?.headline).toBe(
      'Still remembering Preferred format as markdown',
    );
  });

  it('explains that a guess did not overturn something stated', () => {
    const kept = {
      ...change,
      resolution: 'kept-existing' as const,
      keptValue: 'markdown',
      replacedValue: '',
      source: 'inferred' as const,
    };
    expect(presentMemoryChange(kept)?.detail).toBe(
      'This was guessed from how you work, so it did not replace what you told me',
    );
  });

  it('says a stated change came from the person', () => {
    expect(presentMemoryChange(change)?.detail).toBe('Because you said so');
  });

  it('lets the person correct it', () => {
    expect(presentMemoryChange(change)?.action).toBe('correct');
  });

  it('lets the person forget it entirely', () => {
    expect(presentMemoryChange(change)?.secondaryAction).toBe('forget');
  });

  it('is shown quietly rather than as a warning', () => {
    expect(presentMemoryChange(change)?.severity).toBe('info');
  });

  it('can be dismissed', () => {
    expect(presentMemoryChange(change)?.dismissible).toBe(true);
  });

  it('never shows an internal key to the person', () => {
    expect(presentMemoryChange(change)?.headline).not.toContain('preferred-format');
  });

  it('falls back to the key when there is no label', () => {
    const unlabelled = { ...change, label: '' };
    expect(presentMemoryChange(unlabelled)?.headline).toBe(
      'Preferred format is now plain text, not markdown',
    );
  });

  it('does not invent a previous value when there was none', () => {
    const fresh = { ...change, replacedValue: '' };
    expect(presentMemoryChange(fresh)?.headline).toBe('Preferred format is now plain text');
  });
});
