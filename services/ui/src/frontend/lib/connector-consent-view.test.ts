import { describe, expect, it } from 'vitest';

import { presentConnectorConsent } from '@/lib/connector-consent-view';

const simple = {
  source: 'drive',
  reads: ['Team docs'],
  documents: 240,
  actsAs: 'ada',
  warnings: [] as string[],
  readOnly: true,
  needsCarefulConsent: false,
};

describe('presentConnectorConsent', () => {
  it('says what would be connected', () => {
    expect(presentConnectorConsent(simple).headline).toBe('Connect drive');
  });

  it('says what would be read', () => {
    expect(presentConnectorConsent(simple).scope).toBe('Reads: Team docs');
  });

  it('says how much that is', () => {
    expect(presentConnectorConsent(simple).size).toBe('About 240 documents');
  });

  it('says plainly when it would only read', () => {
    expect(presentConnectorConsent(simple).access).toBe('Read only, as ada');
  });

  it('says plainly when it could change things', () => {
    const writes = { ...simple, readOnly: false, warnings: ['this can also create files'] };
    expect(presentConnectorConsent(writes).access).toBe('Can read and change things, as ada');
  });

  it('passes on every warning unchanged', () => {
    const broad = {
      ...simple,
      warnings: ['this covers everything in the account, not a chosen folder'],
      needsCarefulConsent: true,
    };
    expect(presentConnectorConsent(broad).warnings).toEqual([
      'this covers everything in the account, not a chosen folder',
    ]);
  });

  it('lets a plain read-only folder be connected without ceremony', () => {
    expect(presentConnectorConsent(simple).actions).toEqual(['Connect', 'Cancel']);
  });

  it('makes a broad offer confirm what it is agreeing to', () => {
    const broad = { ...simple, warnings: ['this covers everything'], needsCarefulConsent: true };
    expect(presentConnectorConsent(broad).actions).toEqual([
      'I understand — connect',
      'Choose folders instead',
      'Cancel',
    ]);
  });

  it('treats a plain offer as routine', () => {
    expect(presentConnectorConsent(simple).severity).toBe('info');
  });

  it('treats an offer that can change things as worth attention', () => {
    const broad = { ...simple, readOnly: false, warnings: ['x'], needsCarefulConsent: true };
    expect(presentConnectorConsent(broad).severity).toBe('high');
  });

  it('treats a broad read-only offer as worth noticing', () => {
    const broad = { ...simple, warnings: ['x'], needsCarefulConsent: true };
    expect(presentConnectorConsent(broad).severity).toBe('medium');
  });
});
