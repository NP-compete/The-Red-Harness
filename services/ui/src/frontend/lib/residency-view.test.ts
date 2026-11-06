import { describe, expect, it } from 'vitest';

import { presentResidency } from '@/lib/residency-view';

const placement = {
  region: 'eu-west',
  preferredRegion: 'eu-west',
  degraded: false,
  refused: false,
  reason: '',
  allowedRegions: ['eu-west', 'eu-central'],
};

describe('presentResidency', () => {
  it('says where the run is happening', () => {
    expect(presentResidency(placement).label).toBe('Running in eu-west');
  });

  it('says nothing is unusual about the preferred region', () => {
    expect(presentResidency(placement).severity).toBe('none');
  });

  it('says when the run went somewhere other than first choice', () => {
    const elsewhere = { ...placement, region: 'eu-central', degraded: true };
    expect(presentResidency(elsewhere).label).toBe('Running in eu-central, not eu-west');
  });

  it('treats a fallback region as worth noticing', () => {
    const elsewhere = { ...placement, region: 'eu-central', degraded: true };
    expect(presentResidency(elsewhere).severity).toBe('low');
  });

  it('reassures that a fallback is still within policy', () => {
    const elsewhere = { ...placement, region: 'eu-central', degraded: true };
    expect(presentResidency(elsewhere).detail).toBe('This is still within your allowed regions');
  });

  it('says plainly when the run could not be placed', () => {
    const refused = {
      ...placement,
      region: '',
      refused: true,
      reason: 'none of the available regions are allowed; allowed: eu-west, eu-central',
    };
    expect(presentResidency(refused).label).toBe('This run cannot be placed');
  });

  it('treats a refusal as serious', () => {
    const refused = { ...placement, region: '', refused: true, reason: 'x' };
    expect(presentResidency(refused).severity).toBe('high');
  });

  it('carries the refusal reason through', () => {
    const refused = { ...placement, region: '', refused: true, reason: 'nowhere allowed' };
    expect(presentResidency(refused).detail).toBe('nowhere allowed');
  });

  it('never shows a region for a refused run', () => {
    const refused = { ...placement, region: '', refused: true, reason: 'x' };
    expect(presentResidency(refused).label).not.toContain('Running in');
  });

  it('lists where this run is allowed to go', () => {
    expect(presentResidency(placement).allowed).toEqual(['eu-west', 'eu-central']);
  });

  it('offers to see the policy when a run was refused', () => {
    const refused = { ...placement, region: '', refused: true, reason: 'x' };
    expect(presentResidency(refused).action).toBe('view-policy');
  });

  it('offers nothing when the run is placed normally', () => {
    expect(presentResidency(placement).action).toBe('none');
  });
});
