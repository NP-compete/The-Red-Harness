import { describe, expect, it } from 'vitest';

import { presentConnection } from '@/lib/connection-state';

describe('presentConnection', () => {
  it('says nothing while a live stream is flowing', () => {
    const shown = presentConnection({ state: 'streaming', attempts: 0 });
    expect(shown.banner).toBeUndefined();
    expect(shown.canSend).toBe(false);
  });

  it('lets you type when the agent is idle', () => {
    expect(presentConnection({ state: 'idle', attempts: 0 }).canSend).toBe(true);
  });

  it('says it is reconnecting rather than failing', () => {
    const shown = presentConnection({ state: 'reconnecting', attempts: 1 });
    expect(shown.banner).toContain('Reconnecting');
  });

  it('does not lose the answer so far while reconnecting', () => {
    expect(presentConnection({ state: 'reconnecting', attempts: 1 }).keepTranscript).toBe(true);
  });

  it('stops promising after too many attempts', () => {
    const shown = presentConnection({ state: 'reconnecting', attempts: 6 });
    expect(shown.banner).toContain('could not reconnect');
  });

  it('offers a manual retry once it has given up', () => {
    expect(presentConnection({ state: 'reconnecting', attempts: 6 }).action).toBe('retry');
  });

  it('offers nothing to click while it is still trying', () => {
    expect(presentConnection({ state: 'reconnecting', attempts: 1 }).action).toBeUndefined();
  });

  it('says the run continues even though the connection dropped', () => {
    const shown = presentConnection({ state: 'reconnecting', attempts: 1 });
    expect(shown.banner.toLowerCase()).toContain('still running');
  });

  it('reports a finished run plainly', () => {
    const shown = presentConnection({ state: 'idle', attempts: 0 });
    expect(shown.banner).toBeUndefined();
  });

  it('warns when the answer was cut off for good', () => {
    const shown = presentConnection({ state: 'failed', attempts: 6 });
    expect(shown.banner).toContain('did not finish');
    expect(shown.canSend).toBe(true);
  });
});
