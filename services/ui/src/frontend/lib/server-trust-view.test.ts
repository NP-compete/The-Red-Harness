import { describe, expect, it } from 'vitest';

import { presentServerTrust } from '@/lib/server-trust-view';

const check = {
  name: 'mail',
  trust: 'unchanged' as const,
  usable: true,
  reason: '',
};

describe('presentServerTrust', () => {
  it('says an unchanged server is fine without fuss', () => {
    const shown = presentServerTrust(check);
    expect(shown.severity).toBe('none');
    expect(shown.headline).toBe('mail');
  });

  it('is loud when the certificate changed', () => {
    const swapped = {
      ...check,
      trust: 'certificate-changed' as const,
      usable: false,
      reason: 'mail is presenting a different certificate',
    };
    expect(presentServerTrust(swapped).severity).toBe('high');
  });

  it('says plainly what a certificate change might mean', () => {
    const swapped = { ...check, trust: 'certificate-changed' as const, usable: false, reason: 'x' };
    expect(presentServerTrust(swapped).headline).toBe('mail may not be the server you trusted');
  });

  it('is loud about a plain unencrypted connection', () => {
    const insecure = { ...check, trust: 'insecure' as const, usable: false, reason: 'x' };
    expect(presentServerTrust(insecure).severity).toBe('high');
  });

  it('is quieter about a move', () => {
    const moved = { ...check, trust: 'moved' as const, usable: false, reason: 'x' };
    expect(presentServerTrust(moved).severity).toBe('medium');
  });

  it('is quieter still about a tool list that shrank', () => {
    const shrunk = { ...check, trust: 'tools-changed' as const, usable: true, reason: 'x' };
    expect(presentServerTrust(shrunk).severity).toBe('low');
  });

  it('is louder about a tool list that grew, because it is unusable', () => {
    const grown = { ...check, trust: 'tools-changed' as const, usable: false, reason: 'x' };
    expect(presentServerTrust(grown).severity).toBe('medium');
  });

  it('carries the reason through unchanged', () => {
    const moved = { ...check, trust: 'moved' as const, usable: false, reason: 'mail moved from a to b' };
    expect(presentServerTrust(moved).detail).toBe('mail moved from a to b');
  });

  it('asks for confirmation when the server is not usable', () => {
    const moved = { ...check, trust: 'moved' as const, usable: false, reason: 'x' };
    expect(presentServerTrust(moved).action).toBe('confirm');
  });

  it('asks nothing when the server is usable', () => {
    expect(presentServerTrust(check).action).toBe('none');
  });

  it('offers to disconnect a server that cannot be trusted at all', () => {
    const swapped = { ...check, trust: 'certificate-changed' as const, usable: false, reason: 'x' };
    expect(presentServerTrust(swapped).secondaryAction).toBe('disconnect');
  });

  it('treats a server never seen before as something to review, not a fault', () => {
    const fresh = { ...check, trust: 'unknown' as const, usable: false, reason: 'x' };
    expect(presentServerTrust(fresh).severity).toBe('medium');
    expect(presentServerTrust(fresh).headline).toBe('mail has not been connected before');
  });

  it('never says a blocked server is in use', () => {
    const swapped = { ...check, trust: 'certificate-changed' as const, usable: false, reason: 'x' };
    expect(presentServerTrust(swapped).inUse).toBe(false);
  });
});
