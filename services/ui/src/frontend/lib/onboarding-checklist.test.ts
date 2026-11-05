import { describe, expect, it } from 'vitest';

import { presentChecklist } from '@/lib/onboarding-checklist';

const setup = {
  hasSeat: true,
  hasAgent: true,
  connectedServers: 1,
  budgetSet: true,
  approverSet: true,
  firstRunDone: false,
  isAdmin: false,
};

describe('presentChecklist', () => {
  it('lists what is left to do', () => {
    expect(presentChecklist(setup).remaining.map((step) => step.id)).toEqual(['first-run']);
  });

  it('counts progress honestly', () => {
    expect(presentChecklist(setup).progress).toBe('5 of 6 done');
  });

  it('says when everything is done', () => {
    expect(presentChecklist({ ...setup, firstRunDone: true }).complete).toBe(true);
  });

  it('shows no checklist at all once it is complete', () => {
    expect(presentChecklist({ ...setup, firstRunDone: true }).remaining).toEqual([]);
  });

  it('puts the blocking step first', () => {
    const fresh = { ...setup, hasSeat: false, hasAgent: false };
    expect(presentChecklist(fresh).remaining[0].id).toBe('seat');
  });

  it('says a step cannot be done yet when it depends on an earlier one', () => {
    const fresh = { ...setup, hasSeat: false, hasAgent: false };
    const agentStep = presentChecklist(fresh).remaining.find((step) => step.id === 'agent');
    expect(agentStep?.blocked).toBe(true);
  });

  it('says who can unblock a step the person cannot do themselves', () => {
    const fresh = { ...setup, hasSeat: false };
    expect(presentChecklist(fresh).remaining[0].doneBy).toBe('an administrator');
  });

  it('says the person can do their own first run', () => {
    expect(presentChecklist(setup).remaining[0].doneBy).toBe('you');
  });

  it('hides administrator-only steps from an ordinary member', () => {
    const noBudget = { ...setup, budgetSet: false };
    expect(presentChecklist(noBudget).remaining.map((step) => step.id)).toEqual(['first-run']);
  });

  it('shows administrator-only steps to an administrator', () => {
    const noBudget = { ...setup, budgetSet: false, isAdmin: true };
    expect(presentChecklist(noBudget).remaining.map((step) => step.id)).toEqual([
      'budget',
      'first-run',
    ]);
  });

  it('counts only the steps that apply to this person', () => {
    const noBudget = { ...setup, budgetSet: false };
    expect(presentChecklist(noBudget).progress).toBe('4 of 5 done');
  });

  it('asks for a connected server when there are none', () => {
    const bare = { ...setup, connectedServers: 0 };
    expect(presentChecklist(bare).remaining.map((step) => step.id)).toContain('connect');
  });

  it('gives every step something to click', () => {
    const fresh = { ...setup, hasSeat: false, hasAgent: false, connectedServers: 0 };
    for (const step of presentChecklist(fresh).remaining) {
      expect(step.href).not.toBe('');
    }
  });
});
