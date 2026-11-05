import { describe, expect, it } from 'vitest';

import { presentEscalation } from '@/lib/escalation-view';

const now = new Date('2026-10-27T09:00:00Z');

const state = {
  contact: '',
  stepIndex: 0,
  waiting: true,
  repeated: false,
  gaveUp: false,
  approved: false,
  nextAt: '2026-10-27T09:05:00Z',
  reason: '',
  ladder: ['ana', 'team:platform', 'on-call'],
};

describe('presentEscalation', () => {
  it('says who is being waited on', () => {
    expect(presentEscalation(state, now).headline).toBe('Waiting for ana');
  });

  it('says who gets asked next and when', () => {
    expect(presentEscalation(state, now).detail).toBe(
      'If there is no answer in 5 minutes, team:platform will be asked',
    );
  });

  it('says plainly when the last person on the list is being waited on', () => {
    const last = { ...state, stepIndex: 2 };
    expect(presentEscalation(last, now).detail).toBe('There is nobody else to ask after this');
  });

  it('says who was just asked when an escalation happened', () => {
    const moved = { ...state, waiting: false, contact: 'team:platform', stepIndex: 1 };
    expect(presentEscalation(moved, now).headline).toBe('Now asking team:platform');
  });

  it('says when the same person is being asked again', () => {
    const again = { ...state, waiting: false, contact: 'on-call', stepIndex: 2, repeated: true };
    expect(presentEscalation(again, now).headline).toBe('Asking on-call again');
  });

  it('shows the whole ladder so the path is visible', () => {
    expect(presentEscalation(state, now).ladder).toEqual([
      { contact: 'ana', state: 'current' },
      { contact: 'team:platform', state: 'upcoming' },
      { contact: 'on-call', state: 'upcoming' },
    ]);
  });

  it('marks people already asked as done with', () => {
    const later = { ...state, stepIndex: 1 };
    expect(presentEscalation(later, now).ladder[0].state).toBe('asked');
  });

  it('says plainly when nobody answered', () => {
    const over = {
      ...state,
      waiting: false,
      gaveUp: true,
      stepIndex: 2,
      reason: 'nobody answered in 5 hours',
    };
    expect(presentEscalation(over, now).headline).toBe('Nobody answered');
  });

  it('never reads a timeout as approval', () => {
    const over = { ...state, waiting: false, gaveUp: true, stepIndex: 2, reason: 'x' };
    expect(presentEscalation(over, now).approved).toBe(false);
  });

  it('treats giving up as needing attention', () => {
    const over = { ...state, waiting: false, gaveUp: true, stepIndex: 2, reason: 'x' };
    expect(presentEscalation(over, now).severity).toBe('high');
  });

  it('treats ordinary waiting as routine', () => {
    expect(presentEscalation(state, now).severity).toBe('low');
  });

  it('offers to ask someone else sooner', () => {
    expect(presentEscalation(state, now).action).toBe('escalate-now');
  });

  it('offers to start again once it gave up', () => {
    const over = { ...state, waiting: false, gaveUp: true, stepIndex: 2, reason: 'x' };
    expect(presentEscalation(over, now).action).toBe('retry');
  });
});
