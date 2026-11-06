import { describe, expect, it } from 'vitest';

import { presentScopeRefusal } from '@/lib/scope-view';

describe('presentScopeRefusal', () => {
  it('shows nothing when access was allowed', () => {
    expect(presentScopeRefusal({ permitted: true, refusal: null, reason: '' })).toBeNull();
  });

  it('says plainly when something belongs to another team', () => {
    const shown = presentScopeRefusal({
      permitted: false,
      refusal: 'wrong-team',
      reason: 'this belongs to legal',
    });
    expect(shown?.headline).toBe('This belongs to another team');
  });

  it('names the team that owns it', () => {
    const shown = presentScopeRefusal({
      permitted: false,
      refusal: 'wrong-team',
      reason: 'this belongs to legal',
    });
    expect(shown?.detail).toBe('this belongs to legal');
  });

  it('offers to ask for access to another team’s item', () => {
    const shown = presentScopeRefusal({
      permitted: false,
      refusal: 'wrong-team',
      reason: 'x',
    });
    expect(shown?.action).toBe('request-access');
  });

  it('says plainly when only the owner may change something', () => {
    const shown = presentScopeRefusal({
      permitted: false,
      refusal: 'not-owner',
      reason: 'only the owner may change this',
    });
    expect(shown?.headline).toBe('Only the owner can change this');
  });

  it('does not offer to request access to someone’s private item', () => {
    const shown = presentScopeRefusal({
      permitted: false,
      refusal: 'not-owner',
      reason: 'this is private to its owner',
    });
    expect(shown?.action).toBe('none');
  });

  it('gives nothing away across an organisation boundary', () => {
    const shown = presentScopeRefusal({
      permitted: false,
      refusal: 'wrong-org',
      reason: 'this is not available',
    });
    expect(shown?.headline).toBe('Not found');
  });

  it('adds no detail across an organisation boundary', () => {
    const shown = presentScopeRefusal({
      permitted: false,
      refusal: 'wrong-org',
      reason: 'this is not available',
    });
    expect(shown?.detail).toBe('');
  });

  it('offers nothing to do across an organisation boundary', () => {
    const shown = presentScopeRefusal({
      permitted: false,
      refusal: 'wrong-org',
      reason: 'x',
    });
    expect(shown?.action).toBe('none');
  });

  it('does not suggest the item exists across an organisation boundary', () => {
    const shown = presentScopeRefusal({
      permitted: false,
      refusal: 'wrong-org',
      reason: 'x',
    });
    expect(shown?.headline.toLowerCase()).not.toContain('permission');
  });

  it('marks a refusal that can be resolved as low severity', () => {
    const shown = presentScopeRefusal({ permitted: false, refusal: 'wrong-team', reason: 'x' });
    expect(shown?.severity).toBe('low');
  });

  it('marks an unexplainable refusal as nothing to act on', () => {
    const shown = presentScopeRefusal({ permitted: false, refusal: 'wrong-org', reason: 'x' });
    expect(shown?.severity).toBe('none');
  });
});
