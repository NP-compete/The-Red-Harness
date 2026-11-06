import { describe, expect, it } from 'vitest';

import { presentMigration } from '@/lib/state-migration-view';

const current = {
  outcome: 'already-current' as const,
  applied: [] as number[],
  reason: '',
  storedVersion: 3,
  appVersion: 3,
};

describe('presentMigration', () => {
  it('shows nothing when the conversation is already current', () => {
    expect(presentMigration(current)).toBeNull();
  });

  it('shows nothing after a quiet upgrade', () => {
    const migrated = { ...current, outcome: 'migrated' as const, applied: [2, 3], storedVersion: 1 };
    expect(presentMigration(migrated)).toBeNull();
  });

  it('says plainly when a conversation is from a newer version', () => {
    const tooNew = {
      ...current,
      outcome: 'too-new' as const,
      storedVersion: 9,
      reason: 'this was written by a newer version (9)',
    };
    expect(presentMigration(tooNew)?.headline).toBe('This conversation is from a newer version');
  });

  it('explains what that means for the reader', () => {
    const tooNew = { ...current, outcome: 'too-new' as const, storedVersion: 9, reason: 'x' };
    expect(presentMigration(tooNew)?.detail).toBe(
      'It is shown as it was saved, and cannot be changed here',
    );
  });

  it('makes a newer conversation read only', () => {
    const tooNew = { ...current, outcome: 'too-new' as const, storedVersion: 9, reason: 'x' };
    expect(presentMigration(tooNew)?.readOnly).toBe(true);
  });

  it('says plainly when a conversation is too old to open', () => {
    const stuck = {
      ...current,
      outcome: 'no-path' as const,
      storedVersion: 0,
      reason: 'there is no way forward from version 0',
    };
    expect(presentMigration(stuck)?.headline).toBe('This conversation cannot be opened');
  });

  it('gives the reason it cannot be opened', () => {
    const stuck = {
      ...current,
      outcome: 'no-path' as const,
      storedVersion: 0,
      reason: 'there is no way forward from version 0',
    };
    expect(presentMigration(stuck)?.detail).toBe('there is no way forward from version 0');
  });

  it('offers to export a conversation that cannot be opened', () => {
    const stuck = { ...current, outcome: 'no-path' as const, storedVersion: 0, reason: 'x' };
    expect(presentMigration(stuck)?.action).toBe('export');
  });

  it('offers nothing to do about a newer conversation', () => {
    const tooNew = { ...current, outcome: 'too-new' as const, storedVersion: 9, reason: 'x' };
    expect(presentMigration(tooNew)?.action).toBe('none');
  });

  it('treats an unopenable conversation as serious', () => {
    const stuck = { ...current, outcome: 'no-path' as const, storedVersion: 0, reason: 'x' };
    expect(presentMigration(stuck)?.severity).toBe('high');
  });

  it('treats a newer conversation as a caution', () => {
    const tooNew = { ...current, outcome: 'too-new' as const, storedVersion: 9, reason: 'x' };
    expect(presentMigration(tooNew)?.severity).toBe('medium');
  });

  it('never allows editing something it could not fully understand', () => {
    const stuck = { ...current, outcome: 'no-path' as const, storedVersion: 0, reason: 'x' };
    expect(presentMigration(stuck)?.readOnly).toBe(true);
  });
});
