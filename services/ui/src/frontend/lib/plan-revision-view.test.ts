import { describe, expect, it } from 'vitest';

import { presentRevision } from '@/lib/plan-revision-view';

const replaced = {
  blocked: 'check',
  reason: 'the records service is unreachable',
  added: ['ask'],
  narrowed: false,
  needsAgreement: false,
};

describe('presentRevision', () => {
  it('says which step could not be done', () => {
    expect(presentRevision(replaced).headline).toBe('Could not do: check');
  });

  it('says why', () => {
    expect(presentRevision(replaced).reason).toBe('the records service is unreachable');
  });

  it('says what it will do instead', () => {
    expect(presentRevision(replaced).change).toBe('Doing this instead: ask');
  });

  it('names several replacement steps', () => {
    const several = { ...replaced, added: ['ask', 'check'] };
    expect(presentRevision(several).change).toBe('Doing this instead: ask, check');
  });

  it('says plainly when a step was dropped with nothing in its place', () => {
    const dropped = { ...replaced, added: [], narrowed: true, needsAgreement: true };
    expect(presentRevision(dropped).change).toBe('Leaving this out of the plan');
  });

  it('asks before doing less than was agreed', () => {
    const dropped = { ...replaced, added: [], narrowed: true, needsAgreement: true };
    expect(presentRevision(dropped).actions).toEqual(['Carry on without it', 'Stop here']);
  });

  it('offers nothing to decide for a like-for-like swap', () => {
    expect(presentRevision(replaced).actions).toEqual([]);
  });

  it('waits for an answer before narrowing the plan', () => {
    const dropped = { ...replaced, added: [], narrowed: true, needsAgreement: true };
    expect(presentRevision(dropped).blocking).toBe(true);
  });

  it('does not stop the run for a swap', () => {
    expect(presentRevision(replaced).blocking).toBe(false);
  });

  it('treats a narrowed plan as worth noticing', () => {
    const dropped = { ...replaced, added: [], narrowed: true, needsAgreement: true };
    expect(presentRevision(dropped).severity).toBe('medium');
  });

  it('treats a swap as a quiet note', () => {
    expect(presentRevision(replaced).severity).toBe('info');
  });
});
