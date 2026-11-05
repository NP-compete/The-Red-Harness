import { describe, expect, it } from 'vitest';

import { presentAdmission } from '@/lib/admission-view';

const start = { verdict: 'start' as const, position: 0, reason: '', estimatedWaitSeconds: null };

describe('presentAdmission', () => {
  it('shows nothing when a run starts straight away', () => {
    expect(presentAdmission(start)).toBeNull();
  });

  it('says where in the queue a run landed', () => {
    const queued = { ...start, verdict: 'queue' as const, position: 11 };
    expect(presentAdmission(queued)?.headline).toBe('11th in the queue');
  });

  it('says plainly when a run is next', () => {
    const queued = { ...start, verdict: 'queue' as const, position: 1 };
    expect(presentAdmission(queued)?.headline).toBe('Next in the queue');
  });

  it('gives a wait estimate when there is one', () => {
    const queued = {
      ...start,
      verdict: 'queue' as const,
      position: 3,
      estimatedWaitSeconds: 180,
    };
    expect(presentAdmission(queued)?.detail).toBe('about 3 minutes');
  });

  it('says nothing about waiting when there is no estimate', () => {
    const queued = { ...start, verdict: 'queue' as const, position: 3 };
    expect(presentAdmission(queued)?.detail).toBe('');
  });

  it('says plainly when a run was turned away', () => {
    const refused = {
      ...start,
      verdict: 'refused' as const,
      reason: 'this service is shutting down',
    };
    expect(presentAdmission(refused)?.headline).toBe('This run cannot start');
  });

  it('gives the reason it was turned away', () => {
    const refused = {
      ...start,
      verdict: 'refused' as const,
      reason: 'scheduled runs are paused at the moment',
    };
    expect(presentAdmission(refused)?.detail).toBe('scheduled runs are paused at the moment');
  });

  it('lets a queued run be abandoned', () => {
    const queued = { ...start, verdict: 'queue' as const, position: 3 };
    expect(presentAdmission(queued)?.action).toBe('cancel');
  });

  it('offers to try again later when turned away', () => {
    const refused = { ...start, verdict: 'refused' as const, reason: 'x' };
    expect(presentAdmission(refused)?.action).toBe('retry-later');
  });

  it('treats being turned away as worth noticing', () => {
    const refused = { ...start, verdict: 'refused' as const, reason: 'x' };
    expect(presentAdmission(refused)?.severity).toBe('medium');
  });

  it('treats queueing as routine', () => {
    const queued = { ...start, verdict: 'queue' as const, position: 3 };
    expect(presentAdmission(queued)?.severity).toBe('info');
  });

  it('never claims a queued run has started', () => {
    const queued = { ...start, verdict: 'queue' as const, position: 3 };
    expect(presentAdmission(queued)?.started).toBe(false);
  });

  it('never claims a refused run has started', () => {
    const refused = { ...start, verdict: 'refused' as const, reason: 'x' };
    expect(presentAdmission(refused)?.started).toBe(false);
  });
});
