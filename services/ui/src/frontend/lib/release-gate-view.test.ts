import { describe, expect, it } from 'vitest';

import { presentGate } from '@/lib/release-gate-view';

const clean = {
  release: true,
  blockers: [] as string[],
  exceptional: false,
  reason: '',
  nextStep: '',
};

describe('presentGate', () => {
  it('says plainly when a release may go ahead', () => {
    expect(presentGate(clean).headline).toBe('Ready to release');
  });

  it('enables the release button when it is clear', () => {
    expect(presentGate(clean).canRelease).toBe(true);
  });

  it('says plainly when a release is blocked', () => {
    const blocked = {
      ...clean,
      release: false,
      blockers: ['regressed'],
      reason: 'these cases stopped working: a, b',
      nextStep: 'fix the broken cases or accept them deliberately',
    };
    expect(presentGate(blocked).headline).toBe('Not ready to release');
  });

  it('disables the release button when blocked', () => {
    const blocked = { ...clean, release: false, blockers: ['regressed'], reason: 'x' };
    expect(presentGate(blocked).canRelease).toBe(false);
  });

  it('gives the reason it is blocked', () => {
    const blocked = {
      ...clean,
      release: false,
      blockers: ['regressed'],
      reason: 'these cases stopped working: a, b',
    };
    expect(presentGate(blocked).detail).toBe('these cases stopped working: a, b');
  });

  it('describes each blocker in plain words', () => {
    const blocked = {
      ...clean,
      release: false,
      blockers: ['regressed', 'unproven-judge'],
      reason: 'x',
    };
    expect(presentGate(blocked).reasons).toEqual([
      'Something that worked has stopped working',
      'The automatic judge has not been checked against people enough',
    ]);
  });

  it('shows what to do next', () => {
    const blocked = {
      ...clean,
      release: false,
      blockers: ['unreliable-suite'],
      reason: 'x',
      nextStep: 'steady the suite before letting it decide',
    };
    expect(presentGate(blocked).nextStep).toBe('steady the suite before letting it decide');
  });

  it('counts the blockers', () => {
    const blocked = {
      ...clean,
      release: false,
      blockers: ['regressed', 'weak-dataset'],
      reason: 'x',
    };
    expect(presentGate(blocked).blockerCount).toBe(2);
  });

  it('marks an exceptional release so it is visible later', () => {
    const urgent = { ...clean, exceptional: true };
    expect(presentGate(urgent).note).toBe('Released while the error budget was spent');
  });

  it('has no such note for an ordinary release', () => {
    expect(presentGate(clean).note).toBe('');
  });

  it('treats an exceptional release as worth noticing', () => {
    expect(presentGate({ ...clean, exceptional: true }).severity).toBe('medium');
  });

  it('treats a blocked release as serious', () => {
    const blocked = { ...clean, release: false, blockers: ['regressed'], reason: 'x' };
    expect(presentGate(blocked).severity).toBe('high');
  });

  it('treats a clean release as unremarkable', () => {
    expect(presentGate(clean).severity).toBe('none');
  });

  it('never offers a way to release past a blocker', () => {
    const blocked = { ...clean, release: false, blockers: ['regressed'], reason: 'x' };
    expect(presentGate(blocked).override).toBe(false);
  });
});
