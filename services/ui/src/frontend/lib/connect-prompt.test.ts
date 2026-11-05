import { describe, expect, it } from 'vitest';

import { presentConnectPrompt } from '@/lib/connect-prompt';

const pause = {
  server: 'tracker',
  scopes: ['read', 'write'],
  reason: 'to look up incidents',
};

describe('presentConnectPrompt', () => {
  it('names the system to connect', () => {
    expect(presentConnectPrompt(pause).title).toBe('Connect tracker?');
  });

  it('says why the agent wants it', () => {
    expect(presentConnectPrompt(pause).detail).toContain('to look up incidents');
  });

  it('says what access it will be given', () => {
    expect(presentConnectPrompt(pause).permissions).toEqual(['read', 'write']);
  });

  it('is explicit that the access is the person own', () => {
    expect(presentConnectPrompt(pause).note.toLowerCase()).toContain('your own access');
  });

  it('offers to connect and to carry on without', () => {
    expect(presentConnectPrompt(pause).choices).toEqual(['connect', 'skip']);
  });

  it('says what happens if they skip', () => {
    expect(presentConnectPrompt(pause).skipConsequence.toLowerCase()).toContain('without');
  });

  it('handles a system that asks for nothing in particular', () => {
    const shown = presentConnectPrompt({ ...pause, scopes: [] });
    expect(shown.permissions).toEqual([]);
  });

  it('still explains a system with no stated reason', () => {
    const shown = presentConnectPrompt({ ...pause, reason: '' });
    expect(shown.detail.length).toBeGreaterThan(0);
  });

  it('marks a write permission as the one worth reading', () => {
    expect(presentConnectPrompt(pause).changesData).toBe(true);
  });

  it('does not mark a read-only connection', () => {
    const shown = presentConnectPrompt({ ...pause, scopes: ['read'] });
    expect(shown.changesData).toBe(false);
  });
});
