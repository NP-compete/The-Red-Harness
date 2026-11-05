import { describe, expect, it } from 'vitest';

import { presentFeature } from '@/lib/feature-view';

const off = {
  key: 'planner_enabled',
  enabled: false,
  scope: 'agent' as const,
  decided_by: 'default',
  overruled: false,
  missing: [],
  cost: 'Adds a planning model call to every request',
};

describe('presentFeature', () => {
  it('says plainly whether the capability is on', () => {
    expect(presentFeature({ ...off, enabled: true }).state).toBe('on');
  });

  it('says plainly when it is off', () => {
    expect(presentFeature(off).state).toBe('off');
  });

  it('carries what turning it on costs', () => {
    expect(presentFeature(off).cost).toContain('planning model call');
  });

  describe('a capability something above it forbids', () => {
    const refused = { ...off, overruled: true, decided_by: 'deployment' };

    it('is told apart from one simply left off', () => {
      // A switch that will not move needs a different word from one
      // nobody has thrown yet.
      expect(presentFeature(refused).state).toBe('blocked');
    });

    it('names the level that refused it', () => {
      expect(presentFeature(refused).blockedBy).toBe('deployment');
    });

    it('cannot be changed from here', () => {
      expect(presentFeature(refused).changeable).toBe(false);
    });
  });

  describe('a capability waiting on something else', () => {
    const waiting = { ...off, missing: ['sandbox_backend'] };

    it('is told apart from one that is merely off', () => {
      expect(presentFeature(waiting).state).toBe('unavailable');
    });

    it('names what it is waiting for', () => {
      expect(presentFeature(waiting).needs).toEqual(['sandbox_backend']);
    });

    it('cannot be turned on until that arrives', () => {
      expect(presentFeature(waiting).changeable).toBe(false);
    });
  });

  it('an ordinary capability can be changed', () => {
    expect(presentFeature(off).changeable).toBe(true);
  });

  it('reports the level that decided, so the value is explainable', () => {
    expect(presentFeature({ ...off, decided_by: 'agent' }).decidedBy).toBe('agent');
  });
});
