import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { draftStorage, KEEP_FOR_DAYS } from './draftStorage';

const DAY = 24 * 60 * 60 * 1000;

describe('draftStorage', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-03-01T12:00:00Z'));
  });

  afterEach(() => vi.useRealTimers());

  it('keeps what was typed', () => {
    draftStorage.save('t1', 'half a question');
    expect(draftStorage.load('t1')?.text).toBe('half a question');
  });

  it('keeps drafts apart by conversation', () => {
    draftStorage.save('t1', 'one');
    draftStorage.save('t2', 'two');
    expect(draftStorage.load('t1')?.text).toBe('one');
  });

  it('has nothing for a conversation never typed in', () => {
    expect(draftStorage.load('t9')).toBeNull();
  });

  it('records when it was written', () => {
    draftStorage.save('t1', 'half a question');
    expect(draftStorage.load('t1')?.savedAt).toBe(Date.parse('2026-03-01T12:00:00Z'));
  });

  it('reports how old a draft is', () => {
    draftStorage.save('t1', 'half a question');
    vi.setSystemTime(new Date('2026-03-01T12:01:00Z'));
    expect(draftStorage.load('t1')?.ageSeconds).toBe(60);
  });

  it('forgets a draft once it is stale', () => {
    draftStorage.save('t1', 'half a question');
    vi.setSystemTime(new Date(Date.now() + (KEEP_FOR_DAYS + 1) * DAY));
    expect(draftStorage.load('t1')).toBeNull();
  });

  it('still has a draft the day before it goes stale', () => {
    draftStorage.save('t1', 'half a question');
    vi.setSystemTime(new Date(Date.now() + (KEEP_FOR_DAYS - 1) * DAY));
    expect(draftStorage.load('t1')?.text).toBe('half a question');
  });

  it('discards a draft when asked', () => {
    draftStorage.save('t1', 'half a question');
    draftStorage.discard('t1');
    expect(draftStorage.load('t1')).toBeNull();
  });

  it('treats blank text as nothing worth keeping', () => {
    draftStorage.save('t1', '   ');
    expect(draftStorage.load('t1')).toBeNull();
  });

  it('clears an earlier draft when the box is emptied', () => {
    draftStorage.save('t1', 'half a question');
    draftStorage.save('t1', '');
    expect(draftStorage.load('t1')).toBeNull();
  });

  it('survives storage holding something unreadable', () => {
    localStorage.setItem('agent.drafts', 'not json');
    expect(draftStorage.load('t1')).toBeNull();
  });

  it('keeps working after unreadable storage is replaced', () => {
    localStorage.setItem('agent.drafts', 'not json');
    draftStorage.save('t1', 'half a question');
    expect(draftStorage.load('t1')?.text).toBe('half a question');
  });
});
