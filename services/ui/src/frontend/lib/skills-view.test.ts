import { describe, expect, it } from 'vitest';

import { presentSkills } from '@/lib/skills-view';

const skills = [
  { name: 'incident-triage', scope: 'agent' as const, usedThisWeek: 38, editable: false },
  { name: 'sre-habits', scope: 'team' as const, usedThisWeek: 4, editable: true },
  { name: 'my-style', scope: 'user' as const, usedThisWeek: 0, editable: true },
];

describe('presentSkills', () => {
  it('says who each piece of guidance applies to', () => {
    const rows = presentSkills(skills).rows;
    expect(rows.map((row) => row.appliesTo)).toEqual([
      'Everyone using this agent',
      'Your team',
      'Only you',
    ]);
  });

  it('keeps the order the agent reads them in', () => {
    expect(presentSkills(skills).rows.map((r) => r.name)).toEqual([
      'incident-triage',
      'sre-habits',
      'my-style',
    ]);
  });

  it('shows how much each one is actually used', () => {
    expect(presentSkills(skills).rows[0].usage).toBe('used 38 times this week');
  });

  it('says plainly when something is never used', () => {
    expect(presentSkills(skills).rows[2].usage).toBe('not used this week');
  });

  it('uses the singular for one use', () => {
    const once = [{ ...skills[0], usedThisWeek: 1 }];
    expect(presentSkills(once).rows[0].usage).toBe('used once this week');
  });

  it('offers editing only where it is allowed', () => {
    expect(presentSkills(skills).rows.map((r) => r.actions)).toEqual([
      ['view'],
      ['view', 'edit'],
      ['view', 'edit'],
    ]);
  });

  it('counts what is in play', () => {
    expect(presentSkills(skills).count).toBe(3);
  });

  it('flags guidance that nobody uses so it can be retired', () => {
    expect(presentSkills(skills).unused).toEqual(['my-style']);
  });

  it('flags nothing when everything is used', () => {
    const busy = skills.map((s) => ({ ...s, usedThisWeek: 2 }));
    expect(presentSkills(busy).unused).toEqual([]);
  });

  it('handles an agent with no guidance at all', () => {
    const shown = presentSkills([]);
    expect(shown.rows).toEqual([]);
    expect(shown.emptyMessage).toBeTruthy();
  });
});
