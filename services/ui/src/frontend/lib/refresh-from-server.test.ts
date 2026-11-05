import { describe, expect, it } from 'vitest';

import { refreshFromServer } from './refresh-from-server';

const known = (over: Record<string, unknown> = {}) => ({
  id: 'c1',
  title: 'Travel limits',
  preview: 'Travel limits',
  messages: [],
  ...over,
});

const fromServer = (over: Record<string, unknown> = {}) => ({
  id: 'c1',
  title: 'Travel limits',
  serverStatus: 'error',
  forkedFrom: 'parent-1',
  ...over,
});

describe('refreshFromServer', () => {
  it('takes the run status the agent now reports', () => {
    expect(refreshFromServer(known(), fromServer()).serverStatus).toBe('error');
  });

  it('takes a status that has changed since last time', () => {
    const chat = known({ serverStatus: 'interrupted' });
    expect(refreshFromServer(chat, fromServer({ serverStatus: 'success' })).serverStatus).toBe(
      'success',
    );
  });

  it('learns that a conversation was forked', () => {
    expect(refreshFromServer(known(), fromServer()).forkedFrom).toBe('parent-1');
  });

  it('learns where in the parent the fork was taken', () => {
    const refreshed = refreshFromServer(known(), fromServer({ forkedAt: 4 }));
    expect((refreshed as { forkedAt?: number | null }).forkedAt).toBe(4);
  });

  it('keeps the fork point it already knew when the agent says nothing', () => {
    const chat = known({ forkedAt: 4 });
    const refreshed = refreshFromServer(chat, { id: 'c1' });
    expect((refreshed as { forkedAt?: number | null }).forkedAt).toBe(4);
  });

  it('leaves what it already knew when the agent says nothing', () => {
    const chat = known({ serverStatus: 'success', forkedFrom: 'parent-1' });
    const refreshed = refreshFromServer(chat, { id: 'c1' });
    expect(refreshed.serverStatus).toBe('success');
    expect(refreshed.forkedFrom).toBe('parent-1');
  });

  it('does not touch anything else about the conversation', () => {
    const chat = known({ messages: [{ id: 'm1' }], title: 'Mine' });
    const refreshed = refreshFromServer(chat, fromServer({ title: 'Theirs' }));
    expect(refreshed.messages).toHaveLength(1);
    expect(refreshed.title).toBe('Mine');
  });

  it('returns the conversation unchanged when the agent has no record of it', () => {
    const chat = known();
    expect(refreshFromServer(chat, undefined)).toBe(chat);
  });
});
