import { describe, expect, it } from 'vitest';

import { presentStages } from '@/lib/plan-stages-view';

const plan = {
  stages: [['gather', 'fetch'], ['summarise'], ['publish']],
  fates: {
    gather: 'done' as const,
    fetch: 'done' as const,
    summarise: 'running' as const,
    publish: 'waiting' as const,
  },
  depth: 3,
};

describe('presentStages', () => {
  it('keeps the stages in order', () => {
    expect(presentStages(plan).rows.map((row) => row.position)).toEqual([1, 2, 3]);
  });

  it('shows work that happens together in one stage', () => {
    expect(presentStages(plan).rows[0].tasks.map((task) => task.name)).toEqual([
      'gather',
      'fetch',
    ]);
  });

  it('says a stage is finished when all its work is', () => {
    expect(presentStages(plan).rows[0].state).toBe('done');
  });

  it('says a stage is running when any of its work is', () => {
    expect(presentStages(plan).rows[1].state).toBe('running');
  });

  it('says a stage has not started when none of its work has', () => {
    expect(presentStages(plan).rows[2].state).toBe('waiting');
  });

  it('marks a stage as failed when something in it failed', () => {
    const broken = { ...plan, fates: { ...plan.fates, summarise: 'failed' as const } };
    expect(presentStages(broken).rows[1].state).toBe('failed');
  });

  it('marks work that will now be skipped', () => {
    const broken = {
      ...plan,
      fates: { ...plan.fates, summarise: 'failed' as const, publish: 'skipped' as const },
    };
    expect(presentStages(broken).rows[2].state).toBe('skipped');
  });

  it('says how many stages remain', () => {
    expect(presentStages(plan).remaining).toBe(2);
  });

  it('says nothing remains once everything is done', () => {
    const finished = {
      ...plan,
      fates: { gather: 'done', fetch: 'done', summarise: 'done', publish: 'done' } as const,
    };
    expect(presentStages(finished).remaining).toBe(0);
  });

  it('describes how much can happen at once', () => {
    expect(presentStages(plan).summary).toBe('3 stages, 2 tasks can run together');
  });

  it('describes a plan with no parallel work plainly', () => {
    const serial = {
      stages: [['a'], ['b']],
      fates: { a: 'done' as const, b: 'waiting' as const },
      depth: 2,
    };
    expect(presentStages(serial).summary).toBe('2 stages, one task at a time');
  });

  it('says plainly when the plan could not be ordered', () => {
    const broken = { stages: [], fates: {}, depth: 0 };
    expect(presentStages(broken).summary).toBe('This plan cannot be run as written');
  });

  it('shows no rows for a plan that cannot be ordered', () => {
    expect(presentStages({ stages: [], fates: {}, depth: 0 }).rows).toEqual([]);
  });

  it('marks the stage being worked on now', () => {
    expect(presentStages(plan).currentStage).toBe(2);
  });

  it('has no current stage once the work is finished', () => {
    const finished = {
      ...plan,
      fates: { gather: 'done', fetch: 'done', summarise: 'done', publish: 'done' } as const,
    };
    expect(presentStages(finished).currentStage).toBeNull();
  });
});
