import { describe, expect, it } from 'vitest';

import { presentPlan } from '@/lib/plan-view';

const steps = [
  { tool: 'tracker.search', summary: 'Look up last quarter incidents', writes: false },
  { tool: 'docs.list', summary: 'Look up the runbooks', writes: false },
  { tool: 'tracker.create_issue', summary: 'Open a ticket for each gap', writes: true },
];

describe('presentPlan', () => {
  it('lists the steps in order', () => {
    expect(presentPlan(steps).steps.map((s) => s.summary)).toEqual([
      'Look up last quarter incidents',
      'Look up the runbooks',
      'Open a ticket for each gap',
    ]);
  });

  it('marks the steps that change something', () => {
    expect(presentPlan(steps).steps.map((s) => s.changes)).toEqual([false, false, true]);
  });

  it('says how many steps will change something', () => {
    expect(presentPlan(steps).changingCount).toBe(1);
  });

  it('offers to run the whole plan and to run only the research', () => {
    expect(presentPlan(steps).choices).toEqual(['approve', 'read-only', 'edit']);
  });

  it('does not offer a read-only run when nothing changes anything', () => {
    const readOnly = steps.filter((s) => !s.writes);
    expect(presentPlan(readOnly).choices).toEqual(['approve', 'edit']);
  });

  it('summarises a plan that changes nothing as safe to run', () => {
    const readOnly = steps.filter((s) => !s.writes);
    expect(presentPlan(readOnly).headline.toLowerCase()).toContain('nothing');
  });

  it('says plainly what approving will allow', () => {
    expect(presentPlan(steps).headline).toContain('1');
  });

  it('numbers the steps so they can be referred to', () => {
    expect(presentPlan(steps).steps.map((s) => s.number)).toEqual([1, 2, 3]);
  });

  it('refuses to present an empty plan', () => {
    expect(presentPlan([]).steps).toEqual([]);
    expect(presentPlan([]).headline.toLowerCase()).toContain('no steps');
  });

  it('offers nothing to approve for an empty plan', () => {
    expect(presentPlan([]).choices).toEqual([]);
  });
});
