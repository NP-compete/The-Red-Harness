import { describe, expect, it } from 'vitest';

import { presentCapture } from '@/lib/memory-capture-view';

const kept = {
  decision: 'keep' as const,
  text: 'I prefer metric units in every report.',
  reason: '',
};

describe('presentCapture', () => {
  it('says what was remembered', () => {
    expect(presentCapture(kept)?.headline).toBe('Remembered');
  });

  it('shows the memory itself', () => {
    expect(presentCapture(kept)?.text).toBe('I prefer metric units in every report.');
  });

  it('offers a way to take it back', () => {
    expect(presentCapture(kept)?.actions).toEqual(['Forget this']);
  });

  it('asks before keeping something sensitive', () => {
    const asked = {
      decision: 'ask' as const,
      text: 'My doctor is at the north clinic.',
      reason: 'this is sensitive enough to be worth asking about',
    };
    expect(presentCapture(asked)?.headline).toBe('Remember this?');
  });

  it('says why it is asking', () => {
    const asked = {
      decision: 'ask' as const,
      text: 'My doctor is at the north clinic.',
      reason: 'this is sensitive enough to be worth asking about',
    };
    expect(presentCapture(asked)?.detail).toBe(
      'this is sensitive enough to be worth asking about',
    );
  });

  it('offers both answers when asking', () => {
    const asked = { decision: 'ask' as const, text: 'x', reason: 'y' };
    expect(presentCapture(asked)?.actions).toEqual(['Remember', 'Not this']);
  });

  it('waits for an answer rather than assuming one', () => {
    const asked = { decision: 'ask' as const, text: 'x', reason: 'y' };
    expect(presentCapture(asked)?.blocking).toBe(true);
  });

  it('does not block on something already remembered', () => {
    expect(presentCapture(kept)?.blocking).toBe(false);
  });

  it('says nothing at all when nothing was kept', () => {
    const dropped = { decision: 'discard' as const, text: 'x', reason: 'this is only true for now' };
    expect(presentCapture(dropped)).toBeNull();
  });

  it('has no detail to add when a memory was plainly worth keeping', () => {
    expect(presentCapture(kept)?.detail).toBe('');
  });
});
