import { describe, expect, it } from 'vitest';

import { presentMode } from '@/lib/mode-badge';

describe('presentMode', () => {
  it('names the mode in use', () => {
    expect(presentMode({ mode: 'balanced', tier: 'mid' }).label).toBe('Balanced');
  });

  it('says nothing more when the answer came from the expected model', () => {
    expect(presentMode({ mode: 'balanced', tier: 'mid' }).note).toBe('');
  });

  it('says when the answer came from a different model', () => {
    const shown = presentMode({ mode: 'accurate', tier: 'mid', wanted: 'large' });
    expect(shown.note).toContain('was unavailable');
  });

  it('marks a substituted answer so it is not mistaken for the mode asked for', () => {
    expect(presentMode({ mode: 'accurate', tier: 'mid', wanted: 'large' }).substituted).toBe(true);
  });

  it('does not mark an ordinary answer', () => {
    expect(presentMode({ mode: 'fast', tier: 'small' }).substituted).toBe(false);
  });

  it('offers the modes a person may switch to', () => {
    const shown = presentMode({ mode: 'fast', tier: 'small', available: ['fast', 'balanced'] });
    expect(shown.alternatives).toEqual(['balanced']);
  });

  it('never offers the mode already in use', () => {
    const shown = presentMode({ mode: 'fast', tier: 'small', available: ['fast'] });
    expect(shown.alternatives).toEqual([]);
  });

  it('offers nothing when the deployment fixes the mode', () => {
    expect(presentMode({ mode: 'balanced', tier: 'mid' }).alternatives).toEqual([]);
  });

  it('describes what each mode is for', () => {
    expect(presentMode({ mode: 'fast', tier: 'small' }).description.toLowerCase()).toContain(
      'quick',
    );
  });

  it('handles a mode the interface does not know about', () => {
    const shown = presentMode({ mode: 'experimental' as never, tier: 'x' });
    expect(shown.label).toBe('Experimental');
    expect(shown.description).toBe('');
  });
});
