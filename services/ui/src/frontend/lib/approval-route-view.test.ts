import { describe, expect, it } from 'vitest';

import { presentRoute } from '@/lib/approval-route-view';

const route = {
  approvers: ['bo', 'cy'],
  waitMinutes: 15,
  escalateTo: 'on-call',
  onTimeout: 'refuse' as const,
  askNow: true,
  nobodyToAsk: false,
  reason: 'deploy on production needs approval',
};

describe('presentRoute', () => {
  it('says what needs approving', () => {
    expect(presentRoute(route).headline).toBe('deploy on production needs approval');
  });

  it('says who is being asked', () => {
    expect(presentRoute(route).asking).toBe('Asking bo or cy');
  });

  it('names a single approver plainly', () => {
    expect(presentRoute({ ...route, approvers: ['bo'] }).asking).toBe('Asking bo');
  });

  it('says how long they have', () => {
    expect(presentRoute(route).deadline).toBe('15 minutes to answer');
  });

  it('says who it goes to next', () => {
    expect(presentRoute(route).escalation).toBe('Then on-call');
  });

  it('says plainly when there is nobody after them', () => {
    expect(presentRoute({ ...route, escalateTo: '' }).escalation).toBe('Nobody after them');
  });

  it('says plainly that silence means no', () => {
    expect(presentRoute(route).ifNobodyAnswers).toBe('If nobody answers, this will not happen');
  });

  it('says plainly when silence means yes', () => {
    const harmless = { ...route, onTimeout: 'proceed' as const };
    expect(presentRoute(harmless).ifNobodyAnswers).toBe('If nobody answers, this will go ahead');
  });

  it('warns when silence lets something happen', () => {
    const harmless = { ...route, onTimeout: 'proceed' as const };
    expect(presentRoute(harmless).severity).toBe('medium');
  });

  it('treats a refusing default as routine', () => {
    expect(presentRoute(route).severity).toBe('info');
  });

  it('says plainly when there is nobody to ask', () => {
    const stuck = { ...route, approvers: [], nobodyToAsk: true };
    expect(presentRoute(stuck).asking).toBe('There is nobody who can approve this');
  });

  it('treats having nobody to ask as serious', () => {
    const stuck = { ...route, approvers: [], nobodyToAsk: true };
    expect(presentRoute(stuck).severity).toBe('high');
  });

  it('says when the question is waiting rather than sent', () => {
    const queued = { ...route, askNow: false };
    expect(presentRoute(queued).state).toBe('waiting to be asked');
  });

  it('says when the question has gone out', () => {
    expect(presentRoute(route).state).toBe('asked');
  });

  it('offers to ask someone else', () => {
    expect(presentRoute(route).action).toBe('choose-approver');
  });
});
