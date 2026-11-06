import { describe, expect, it } from 'vitest';

import { presentBundle } from '@/lib/support-bundle-view';

const now = new Date('2026-10-27T09:00:00Z');

const bundle = {
  sections: ['versions', 'config', 'recent-errors'],
  redactions: 1,
  sizeBytes: 4_200,
  createdAt: '2026-10-27T08:00:00Z',
  expiresAt: '2026-11-03T08:00:00Z',
  downloadUrl: '/bundles/abc',
};

describe('presentBundle', () => {
  it('lists what is inside', () => {
    expect(presentBundle(bundle, now).contents).toEqual([
      'versions',
      'config',
      'recent-errors',
    ]);
  });

  it('says how many secrets were taken out', () => {
    expect(presentBundle(bundle, now).redactionNote).toBe('1 secret was removed');
  });

  it('uses the plural for several', () => {
    expect(presentBundle({ ...bundle, redactions: 3 }, now).redactionNote).toBe(
      '3 secrets were removed',
    );
  });

  it('says plainly when nothing needed removing', () => {
    expect(presentBundle({ ...bundle, redactions: 0 }, now).redactionNote).toBe(
      'No secrets were found to remove',
    );
  });

  it('shows the size in units a person reads', () => {
    expect(presentBundle(bundle, now).size).toBe('4.2 kB');
  });

  it('says how long the bundle will be kept', () => {
    expect(presentBundle(bundle, now).expires).toBe('deleted in 7 days');
  });

  it('offers the download while it is available', () => {
    expect(presentBundle(bundle, now).downloadUrl).toBe('/bundles/abc');
  });

  it('withholds an expired download', () => {
    const stale = { ...bundle, expiresAt: '2026-10-26T08:00:00Z' };
    expect(presentBundle(stale, now).downloadUrl).toBeNull();
  });

  it('says plainly when the bundle has gone', () => {
    const stale = { ...bundle, expiresAt: '2026-10-26T08:00:00Z' };
    expect(presentBundle(stale, now).expires).toBe('deleted');
  });

  it('lets an expired bundle be made again', () => {
    const stale = { ...bundle, expiresAt: '2026-10-26T08:00:00Z' };
    expect(presentBundle(stale, now).action).toBe('rebuild');
  });

  it('offers a download rather than a rebuild while it is live', () => {
    expect(presentBundle(bundle, now).action).toBe('download');
  });

  it('reminds the person to check it before sending it on', () => {
    expect(presentBundle(bundle, now).advice).toBe(
      'Review the contents before sharing this outside your organisation',
    );
  });

  it('never claims a bundle is free of sensitive information', () => {
    const shown = presentBundle(bundle, now);
    expect(`${shown.redactionNote} ${shown.advice}`.toLowerCase()).not.toContain('safe to share');
  });
});
