import { describe, expect, it } from 'vitest';

import { presentImport } from '@/lib/import-view';

const accepted = {
  verdict: 'accept' as const,
  reason: '',
  rowsTaken: 495,
  trusted: true,
};

describe('presentImport', () => {
  it('says how much would be taken in', () => {
    expect(presentImport(accepted).headline).toBe('Ready to import 495 rows');
  });

  it('says plainly when a file is refused', () => {
    const refused = { ...accepted, verdict: 'refuse' as const, reason: 'this file is incomplete', rowsTaken: 0 };
    expect(presentImport(refused).headline).toBe('This file cannot be imported');
  });

  it('gives the reason for a refusal', () => {
    const refused = { ...accepted, verdict: 'refuse' as const, reason: 'this file is incomplete', rowsTaken: 0 };
    expect(presentImport(refused).detail).toBe('this file is incomplete');
  });

  it('says plainly when a file is waiting on someone', () => {
    const held = {
      ...accepted,
      verdict: 'hold' as const,
      reason: 'this holds personal data with no recorded consent',
      rowsTaken: 0,
    };
    expect(presentImport(held).headline).toBe('This file needs approval first');
  });

  it('marks data that came from outside', () => {
    expect(presentImport({ ...accepted, trusted: false }).provenance).toBe(
      'From outside — treated as unverified',
    );
  });

  it('says nothing about provenance for data from inside', () => {
    expect(presentImport(accepted).provenance).toBe('');
  });

  it('offers to go ahead with an accepted file', () => {
    expect(presentImport(accepted).actions).toEqual(['Import', 'Cancel']);
  });

  it('offers to ask for approval on a held file', () => {
    const held = { ...accepted, verdict: 'hold' as const, reason: 'x', rowsTaken: 0 };
    expect(presentImport(held).actions).toEqual(['Request approval', 'Cancel']);
  });

  it('offers only a way out of a refused file', () => {
    const refused = { ...accepted, verdict: 'refuse' as const, reason: 'x', rowsTaken: 0 };
    expect(presentImport(refused).actions).toEqual(['Cancel']);
  });

  it('treats a refusal as worth real attention', () => {
    const refused = { ...accepted, verdict: 'refuse' as const, reason: 'x', rowsTaken: 0 };
    expect(presentImport(refused).severity).toBe('high');
  });

  it('treats a hold as something to act on, not an error', () => {
    const held = { ...accepted, verdict: 'hold' as const, reason: 'x', rowsTaken: 0 };
    expect(presentImport(held).severity).toBe('medium');
  });

  it('treats an accepted file as routine', () => {
    expect(presentImport(accepted).severity).toBe('info');
  });
});
