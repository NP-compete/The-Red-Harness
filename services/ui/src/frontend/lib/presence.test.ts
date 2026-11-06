import { describe, expect, it } from 'vitest';

import { presentPresence } from '@/lib/presence';

const me = 'me@example.com';

describe('presentPresence', () => {
  it('says nobody else is here when you are alone', () => {
    const shown = presentPresence({ me, viewers: [me] });
    expect(shown.others).toEqual([]);
    expect(shown.summary).toBe('Only you');
  });

  it('lists the other people viewing', () => {
    const shown = presentPresence({ me, viewers: [me, 'a@example.com', 'b@example.com'] });
    expect(shown.others).toEqual(['a@example.com', 'b@example.com']);
  });

  it('never lists you among the others', () => {
    const shown = presentPresence({ me, viewers: ['a@example.com', me] });
    expect(shown.others).not.toContain(me);
  });

  it('counts people once however many times they appear', () => {
    const shown = presentPresence({ me, viewers: [me, 'a@example.com', 'a@example.com'] });
    expect(shown.others).toEqual(['a@example.com']);
  });

  it('says who is running the agent', () => {
    const shown = presentPresence({ me, viewers: [me, 'a@example.com'], holder: 'a@example.com' });
    expect(shown.summary).toContain('a@example.com is running');
  });

  it('tells you when it is you who is running', () => {
    const shown = presentPresence({ me, viewers: [me], holder: me });
    expect(shown.summary).toBe('You are running this');
  });

  it('says you cannot send while somebody else holds it', () => {
    const shown = presentPresence({ me, viewers: [me, 'a@example.com'], holder: 'a@example.com' });
    expect(shown.canSend).toBe(false);
  });

  it('lets you send when nobody holds it', () => {
    expect(presentPresence({ me, viewers: [me] }).canSend).toBe(true);
  });

  it('lets you send when you are the holder', () => {
    expect(presentPresence({ me, viewers: [me], holder: me }).canSend).toBe(true);
  });

  it('offers to ask for the conversation when somebody else holds it', () => {
    const shown = presentPresence({ me, viewers: [me, 'a@example.com'], holder: 'a@example.com' });
    expect(shown.action).toBe('request-handover');
  });

  it('offers no action when you can already send', () => {
    expect(presentPresence({ me, viewers: [me] }).action).toBeUndefined();
  });
});
