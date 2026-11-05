import { describe, expect, it } from 'vitest';

import { presentSecretWarning } from '@/lib/secret-warning-view';

const report = {
  findings: [{ kind: 'api-key', line: 2, excerpt: 'API_KEY=********' }],
  safeToSend: false,
  summary: '1 possible credentials found (api-key)',
};

describe('presentSecretWarning', () => {
  it('shows nothing when the text is clean', () => {
    expect(presentSecretWarning({ findings: [], safeToSend: true, summary: '' })).toBeNull();
  });

  it('says what was found in plain words', () => {
    expect(presentSecretWarning(report)?.headline).toBe(
      'This message looks like it contains an API key',
    );
  });

  it('names a private key as a private key', () => {
    const keyReport = {
      ...report,
      findings: [{ kind: 'private-key', line: 1, excerpt: '-----BEGIN RSA PRIVATE KEY-----' }],
    };
    expect(presentSecretWarning(keyReport)?.headline).toContain('private key');
  });

  it('counts several findings rather than naming only the first', () => {
    const many = {
      ...report,
      findings: [
        { kind: 'api-key', line: 2, excerpt: 'API_KEY=********' },
        { kind: 'password', line: 3, excerpt: 'password=********' },
      ],
    };
    expect(presentSecretWarning(many)?.headline).toBe(
      'This message looks like it contains 2 credentials',
    );
  });

  it('points at the lines so they can be checked', () => {
    expect(presentSecretWarning(report)?.locations).toEqual(['line 2']);
  });

  it('shows the masked excerpt rather than the value', () => {
    expect(presentSecretWarning(report)?.excerpts).toEqual(['API_KEY=********']);
  });

  it('blocks sending by default', () => {
    expect(presentSecretWarning(report)?.blocked).toBe(true);
  });

  it('lets the person send anyway once they have looked', () => {
    expect(presentSecretWarning(report)?.override).toBe('send anyway');
  });

  it('warns that sending anyway is recorded', () => {
    expect(presentSecretWarning(report)?.overrideNote).toContain('recorded');
  });

  it('does not block when the scan found nothing but still reported', () => {
    const clean = { ...report, findings: [], safeToSend: true, summary: '' };
    expect(presentSecretWarning(clean)).toBeNull();
  });

  it('never puts the raw summary in front of the person', () => {
    expect(presentSecretWarning(report)?.headline).not.toContain('api-key');
  });
});
