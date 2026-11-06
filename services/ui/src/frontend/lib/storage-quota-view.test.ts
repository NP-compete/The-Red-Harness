import { describe, expect, it } from 'vitest';

import { presentStorage } from '@/lib/storage-quota-view';

const fine = {
  state: 'fine' as const,
  shareUsed: 0.1,
  remainingBytes: 9_000_000,
  couldFreeBytes: 0,
  mayAccept: true,
  reason: '',
};

describe('presentStorage', () => {
  it('shows nothing while there is plenty of room', () => {
    expect(presentStorage(fine)).toBeNull();
  });

  it('warns when the store is nearly full', () => {
    const nearly = { ...fine, state: 'nearly-full' as const, shareUsed: 0.85, remainingBytes: 1_500_000 };
    expect(presentStorage(nearly)?.headline).toBe('1.5 MB of storage left');
  });

  it('says plainly when the store is full', () => {
    const full = {
      ...fine,
      state: 'full' as const,
      shareUsed: 1,
      remainingBytes: 0,
      reason: 'storage is full',
    };
    expect(presentStorage(full)?.headline).toBe('Storage is full');
  });

  it('says what can still be done when full', () => {
    const full = { ...fine, state: 'full' as const, shareUsed: 1, remainingBytes: 0, reason: 'x' };
    expect(presentStorage(full)?.stillPossible).toBe('You can still read and delete what is here');
  });

  it('says how much could be cleared', () => {
    const full = {
      ...fine,
      state: 'full' as const,
      shareUsed: 1,
      remainingBytes: 0,
      couldFreeBytes: 2_000_000,
      reason: 'x',
    };
    expect(presentStorage(full)?.couldFree).toBe('2 MB could be cleared');
  });

  it('says nothing about clearing when there is nothing to clear', () => {
    const full = { ...fine, state: 'full' as const, shareUsed: 1, remainingBytes: 0, reason: 'x' };
    expect(presentStorage(full)?.couldFree).toBe('');
  });

  it('offers to clear old data when there is some', () => {
    const full = {
      ...fine,
      state: 'full' as const,
      couldFreeBytes: 2_000_000,
      remainingBytes: 0,
      reason: 'x',
    };
    expect(presentStorage(full)?.action).toBe('clear-old');
  });

  it('offers to ask for more room when nothing can be cleared', () => {
    const full = { ...fine, state: 'full' as const, remainingBytes: 0, reason: 'x' };
    expect(presentStorage(full)?.action).toBe('request-more');
  });

  it('explains a refused upload', () => {
    const refused = {
      ...fine,
      state: 'nearly-full' as const,
      mayAccept: false,
      reason: 'this is 400 kB too large to store',
    };
    expect(presentStorage(refused)?.detail).toBe('this is 400 kB too large to store');
  });

  it('blocks uploading when an upload would not fit', () => {
    const refused = { ...fine, mayAccept: false, reason: 'x' };
    expect(presentStorage(refused)?.canUpload).toBe(false);
  });

  it('allows uploading while there is room', () => {
    const nearly = { ...fine, state: 'nearly-full' as const, shareUsed: 0.85 };
    expect(presentStorage(nearly)?.canUpload).toBe(true);
  });

  it('gives the share used for a bar', () => {
    const nearly = { ...fine, state: 'nearly-full' as const, shareUsed: 0.85 };
    expect(presentStorage(nearly)?.bar).toBe(0.85);
  });

  it('treats a full store as serious', () => {
    const full = { ...fine, state: 'full' as const, remainingBytes: 0, reason: 'x' };
    expect(presentStorage(full)?.severity).toBe('high');
  });

  it('treats a nearly full store as a warning', () => {
    const nearly = { ...fine, state: 'nearly-full' as const, shareUsed: 0.85 };
    expect(presentStorage(nearly)?.severity).toBe('medium');
  });
});
