import { describe, expect, it } from 'vitest';

import { presentHeadless } from '@/lib/headless';

const agent = {
  name: 'Ticket triage',
  trigger: 'event' as const,
  actsAs: 'the reporting person',
  state: 'healthy' as const,
  lastRun: '14:08',
};

describe('presentHeadless', () => {
  it('says when an agent runs', () => {
    expect(presentHeadless([{ ...agent, trigger: 'schedule', schedule: 'daily, 07:00' }])
      .rows[0].when).toBe('daily, 07:00');
  });

  it('describes an event-driven agent without inventing a schedule', () => {
    expect(presentHeadless([agent]).rows[0].when).toBe('on an event');
  });

  it('says who it acts as, because that decides what it can reach', () => {
    expect(presentHeadless([agent]).rows[0].actsAs).toBe('the reporting person');
  });

  it('flags an agent waiting for a person', () => {
    const rows = presentHeadless([{ ...agent, state: 'waiting' }]).rows;
    expect(rows[0].needsAttention).toBe(true);
  });

  it('flags a stuck agent', () => {
    expect(presentHeadless([{ ...agent, state: 'stuck' }]).rows[0].needsAttention).toBe(true);
  });

  it('does not flag a healthy agent', () => {
    expect(presentHeadless([agent]).rows[0].needsAttention).toBe(false);
  });

  it('puts the agents needing attention first', () => {
    const rows = presentHeadless([agent, { ...agent, name: 'Stuck one', state: 'stuck' }]).rows;
    expect(rows[0].name).toBe('Stuck one');
  });

  it('counts how many need a person', () => {
    const shown = presentHeadless([agent, { ...agent, state: 'waiting' }]);
    expect(shown.needingAttention).toBe(1);
  });

  it('offers to stop a stuck agent and nothing else', () => {
    expect(presentHeadless([{ ...agent, state: 'stuck' }]).rows[0].actions).toEqual(['stop']);
  });

  it('offers to approve or refuse for one that is waiting', () => {
    expect(presentHeadless([{ ...agent, state: 'waiting' }]).rows[0].actions).toEqual([
      'approve',
      'refuse',
    ]);
  });

  it('shows an empty list without inventing agents', () => {
    expect(presentHeadless([]).rows).toEqual([]);
  });
});
