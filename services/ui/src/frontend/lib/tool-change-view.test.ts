import { describe, expect, it } from 'vitest';

import { presentToolChange } from '@/lib/tool-change-view';

const change = {
  tool: 'send-email',
  changes: ['parameter-added'],
  needsReapproval: true,
  summary: 'send-email gained bcc',
  approvedOn: '2026-09-01T10:00:00Z',
};

describe('presentToolChange', () => {
  it('says the tool is not the one that was approved', () => {
    expect(presentToolChange(change).headline).toBe('send-email has changed since you approved it');
  });

  it('shows what changed in the words it was given', () => {
    expect(presentToolChange(change).detail).toBe('send-email gained bcc');
  });

  it('says when the old approval was given', () => {
    expect(presentToolChange(change).approvedOn).toBe('1 September 2026');
  });

  it('asks for a fresh answer when the change widens the tool', () => {
    expect(presentToolChange(change).action).toBe('reapprove');
  });

  it('does not ask again for a change that narrows the tool', () => {
    const narrowed = {
      ...change,
      changes: ['parameter-removed'],
      needsReapproval: false,
      summary: 'send-email lost bcc',
    };
    expect(presentToolChange(narrowed).action).toBe('none');
  });

  it('still tells the person about a narrowing change', () => {
    const narrowed = { ...change, needsReapproval: false, summary: 'send-email lost bcc' };
    expect(presentToolChange(narrowed).detail).toBe('send-email lost bcc');
  });

  it('is loud about a tool that moved to a different server', () => {
    const moved = {
      ...change,
      changes: ['server-changed'],
      summary: 'send-email moved from mail to relay',
    };
    expect(presentToolChange(moved).severity).toBe('high');
  });

  it('is loud about a rewritten description', () => {
    const reworded = { ...change, changes: ['description-changed'] };
    expect(presentToolChange(reworded).severity).toBe('high');
  });

  it('is quieter about a new optional parameter', () => {
    expect(presentToolChange(change).severity).toBe('medium');
  });

  it('is quietest about a change that needs no answer', () => {
    const narrowed = { ...change, changes: ['parameter-removed'], needsReapproval: false };
    expect(presentToolChange(narrowed).severity).toBe('low');
  });

  it('blocks the call until the question is answered', () => {
    expect(presentToolChange(change).blocking).toBe(true);
  });

  it('does not block for a change that needs no answer', () => {
    expect(presentToolChange({ ...change, needsReapproval: false }).blocking).toBe(false);
  });

  it('shows nothing at all when nothing changed', () => {
    const same = { ...change, changes: [], needsReapproval: false, summary: '' };
    expect(presentToolChange(same)).toBeNull();
  });
});
