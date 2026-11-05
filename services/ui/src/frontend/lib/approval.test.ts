import { describe, expect, it } from 'vitest';

import { presentApproval } from '@/lib/approval';

const base = {
  tool: 'tracker.create_issue',
  risk: 'medium' as const,
  reason: 'Writes to a shared tracker.',
};

describe('presentApproval', () => {
  it('asks a question rather than announcing a state', () => {
    expect(presentApproval(base).title.endsWith('?')).toBe(true);
  });

  it('always says why it is asking', () => {
    expect(presentApproval(base).reason).toBe('Writes to a shared tracker.');
  });

  it('falls back to a reason when the policy gave none', () => {
    expect(presentApproval({ ...base, reason: '' }).reason.length).toBeGreaterThan(0);
  });

  it('offers approve and refuse, with refuse always available', () => {
    const choices = presentApproval(base).choices.map((choice) => choice.kind);
    expect(choices).toContain('approve-once');
    expect(choices).toContain('refuse');
  });

  it('puts refuse last so it is not the reflexive click', () => {
    const choices = presentApproval(base).choices;
    expect(choices[choices.length - 1].kind).toBe('refuse');
  });

  it('offers to approve the rest of a batch when more calls are pending', () => {
    const choices = presentApproval({ ...base, pending: 3 }).choices;
    const batch = choices.find((choice) => choice.kind === 'approve-run');
    expect(batch?.label).toBe('Yes to all 3');
  });

  it('does not offer a batch approval for a single call', () => {
    const choices = presentApproval({ ...base, pending: 1 }).choices;
    expect(choices.some((choice) => choice.kind === 'approve-run')).toBe(false);
  });

  it('marks a high-risk request so it reads differently', () => {
    expect(presentApproval({ ...base, risk: 'high' }).emphasis).toBe('high');
  });

  it('says when a run has read outside content, because that is why it is asking', () => {
    const shown = presentApproval({ ...base, escalated: true });
    expect(shown.note).toContain('outside');
  });

  it('adds no note when nothing escalated the request', () => {
    expect(presentApproval(base).note).toBeUndefined();
  });
});
