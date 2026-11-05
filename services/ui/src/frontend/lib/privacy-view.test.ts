import { describe, expect, it } from 'vitest';

import { presentPrivacy } from '@/lib/privacy-view';

const settings = {
  region: 'eu-west-1',
  retentionDays: 400,
  usedForTraining: false,
  maskingEnabled: true,
  adminCanReadContent: false,
};

describe('presentPrivacy', () => {
  it('says where conversations are kept', () => {
    expect(presentPrivacy(settings).rows[0].detail).toContain('eu-west-1');
  });

  it('says how long they are kept, in something other than days', () => {
    expect(presentPrivacy(settings).rows[1].detail).toContain('13 months');
  });

  it('keeps short retention in days', () => {
    const shown = presentPrivacy({ ...settings, retentionDays: 20 });
    expect(shown.rows[1].detail).toContain('20 days');
  });

  it('states plainly that nothing trains a model', () => {
    const row = presentPrivacy(settings).rows.find((r) => r.title === 'Model training');
    expect(row?.detail.toLowerCase()).toContain('not used');
    expect(row?.good).toBe(true);
  });

  it('does not pretend when conversations are used for training', () => {
    const shown = presentPrivacy({ ...settings, usedForTraining: true });
    const row = shown.rows.find((r) => r.title === 'Model training');
    expect(row?.good).toBe(false);
  });

  it('says whether personal details are masked', () => {
    const row = presentPrivacy(settings).rows.find((r) => r.title === 'Personal details');
    expect(row?.good).toBe(true);
  });

  it('is honest when masking is off', () => {
    const shown = presentPrivacy({ ...settings, maskingEnabled: false });
    expect(shown.rows.find((r) => r.title === 'Personal details')?.good).toBe(false);
  });

  it('says what an administrator can see', () => {
    const row = presentPrivacy(settings).rows.find((r) => r.title === 'Administrators');
    expect(row?.detail.toLowerCase()).toContain('not what you said');
  });

  it('says so when administrators can read content', () => {
    const shown = presentPrivacy({ ...settings, adminCanReadContent: true });
    const row = shown.rows.find((r) => r.title === 'Administrators');
    expect(row?.good).toBe(false);
  });

  it('always offers to download and delete', () => {
    expect(presentPrivacy(settings).actions).toEqual(['download', 'delete']);
  });

  it('counts anything a person might object to', () => {
    const shown = presentPrivacy({ ...settings, usedForTraining: true, maskingEnabled: false });
    expect(shown.concerns).toBe(2);
  });

  it('reports no concerns when everything is favourable', () => {
    expect(presentPrivacy(settings).concerns).toBe(0);
  });
});
