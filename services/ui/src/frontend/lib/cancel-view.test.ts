import { describe, expect, it } from 'vitest';

import { presentStopControl } from '@/lib/cancel-view';

const run = {
  stage: 'thinking' as const,
  tool: '',
  reversible: true,
  isOwner: true,
  isOperator: false,
};

describe('presentStopControl', () => {
  it('offers to stop a run that is thinking', () => {
    expect(presentStopControl(run).enabled).toBe(true);
  });

  it('labels the control plainly', () => {
    expect(presentStopControl(run).label).toBe('Stop');
  });

  it('warns before abandoning a call that cannot be undone', () => {
    const writing = { ...run, stage: 'calling-tool' as const, tool: 'charge-card', reversible: false };
    expect(presentStopControl(writing).confirm).toContain('charge-card');
  });

  it('says the call will finish before anything stops', () => {
    const writing = { ...run, stage: 'calling-tool' as const, tool: 'charge-card', reversible: false };
    expect(presentStopControl(writing).confirm).toContain('will finish');
  });

  it('asks for no confirmation when there is nothing to lose', () => {
    expect(presentStopControl(run).confirm).toBe('');
  });

  it('asks for no confirmation on a reversible call', () => {
    const reading = { ...run, stage: 'calling-tool' as const, tool: 'search', reversible: true };
    expect(presentStopControl(reading).confirm).toBe('');
  });

  it('labels the control honestly while a write is in flight', () => {
    const writing = { ...run, stage: 'calling-tool' as const, tool: 'charge-card', reversible: false };
    expect(presentStopControl(writing).label).toBe('Stop after this step');
  });

  it('does not let a bystander stop someone elses run', () => {
    expect(presentStopControl({ ...run, isOwner: false }).enabled).toBe(false);
  });

  it('tells a bystander why the control is off', () => {
    expect(presentStopControl({ ...run, isOwner: false }).blockedReason).toContain('not yours');
  });

  it('lets an operator stop any run', () => {
    expect(presentStopControl({ ...run, isOwner: false, isOperator: true }).enabled).toBe(true);
  });

  it('warns an operator that the run belongs to someone else', () => {
    const shown = presentStopControl({ ...run, isOwner: false, isOperator: true });
    expect(shown.confirm).toContain('someone else');
  });

  it('turns the control off once the run has ended', () => {
    expect(presentStopControl({ ...run, stage: 'done' }).enabled).toBe(false);
  });

  it('says a finished run has nothing left to stop', () => {
    expect(presentStopControl({ ...run, stage: 'done' }).blockedReason).toContain('already');
  });

  it('offers to stop a run that is waiting on a person', () => {
    expect(presentStopControl({ ...run, stage: 'awaiting-approval' }).enabled).toBe(true);
  });
});
