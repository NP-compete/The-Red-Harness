import { describe, expect, it } from 'vitest';

import { presentIngestion } from '@/lib/ingestion-view';

const accepted = {
  name: 'handbook.pdf',
  permitted: true,
  refusal: null as string | null,
  retryAfterScan: false,
  reason: '',
};

describe('presentIngestion', () => {
  it('shows nothing for a document that was taken in', () => {
    expect(presentIngestion(accepted)).toBeNull();
  });

  it('names the document that was turned away', () => {
    const refused = {
      ...accepted,
      permitted: false,
      refusal: 'licence',
      reason: 'this may not be copied into the knowledge base',
    };
    expect(presentIngestion(refused)?.headline).toBe('handbook.pdf was not added');
  });

  it('gives the reason in the words it was given', () => {
    const refused = {
      ...accepted,
      permitted: false,
      refusal: 'licence',
      reason: 'this may not be copied into the knowledge base',
    };
    expect(presentIngestion(refused)?.detail).toBe(
      'this may not be copied into the knowledge base',
    );
  });

  it('says a document still being checked will be tried again', () => {
    const waiting = {
      ...accepted,
      permitted: false,
      refusal: 'not-scanned',
      retryAfterScan: true,
      reason: 'this has not been checked yet',
    };
    expect(presentIngestion(waiting)?.headline).toBe('handbook.pdf is still being checked');
  });

  it('treats a document awaiting a check as routine', () => {
    const waiting = { ...accepted, permitted: false, refusal: 'not-scanned', retryAfterScan: true, reason: 'x' };
    expect(presentIngestion(waiting)?.severity).toBe('info');
  });

  it('treats something unsafe as serious', () => {
    const unsafe = { ...accepted, permitted: false, refusal: 'unsafe', reason: 'x' };
    expect(presentIngestion(unsafe)?.severity).toBe('high');
  });

  it('treats a policy refusal as ordinary', () => {
    const refused = { ...accepted, permitted: false, refusal: 'licence', reason: 'x' };
    expect(presentIngestion(refused)?.severity).toBe('medium');
  });

  it('offers to remove personal data when that is the only problem', () => {
    const personal = {
      ...accepted,
      permitted: false,
      refusal: 'personal-data',
      reason: 'scrub the personal data out and it can be taken in',
    };
    expect(presentIngestion(personal)?.action).toBe('scrub');
  });

  it('offers to split something too large', () => {
    const big = { ...accepted, permitted: false, refusal: 'too-large', reason: 'x' };
    expect(presentIngestion(big)?.action).toBe('split');
  });

  it('offers nothing for something unsafe', () => {
    const unsafe = { ...accepted, permitted: false, refusal: 'unsafe', reason: 'x' };
    expect(presentIngestion(unsafe)?.action).toBe('none');
  });

  it('offers nothing while a check is still running', () => {
    const waiting = { ...accepted, permitted: false, refusal: 'not-scanned', retryAfterScan: true, reason: 'x' };
    expect(presentIngestion(waiting)?.action).toBe('none');
  });

  it('says whether it is worth trying again later', () => {
    const waiting = { ...accepted, permitted: false, refusal: 'not-scanned', retryAfterScan: true, reason: 'x' };
    expect(presentIngestion(waiting)?.willRetry).toBe(true);
  });

  it('does not promise a retry for a refusal that will not change', () => {
    const refused = { ...accepted, permitted: false, refusal: 'licence', reason: 'x' };
    expect(presentIngestion(refused)?.willRetry).toBe(false);
  });
});
