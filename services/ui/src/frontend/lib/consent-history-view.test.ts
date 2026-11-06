import { describe, expect, it } from 'vitest';

import { presentConsentHistory } from '@/lib/consent-history-view';

const now = new Date('2026-10-27T09:00:00Z');

const receipts = [
  {
    receiptId: 'r1',
    purpose: 'improve-the-system',
    granted: true,
    at: '2026-09-01T09:00:00Z',
    wording: 'Allow my conversations to be studied to improve the system',
  },
  {
    receiptId: 'r2',
    purpose: 'improve-the-system',
    granted: false,
    at: '2026-10-01T09:00:00Z',
    wording: 'Allow my conversations to be studied to improve the system',
  },
  {
    receiptId: 'r3',
    purpose: 'share-with-partners',
    granted: true,
    at: '2026-10-20T09:00:00Z',
    wording: 'Allow my data to be shared with partners',
  },
];

describe('presentConsentHistory', () => {
  it('shows one row per purpose, not per event', () => {
    expect(presentConsentHistory(receipts, now).rows).toHaveLength(2);
  });

  it('shows the current state of each purpose', () => {
    const rows = presentConsentHistory(receipts, now).rows;
    expect(rows.find((row) => row.purpose === 'improve-the-system')?.granted).toBe(false);
  });

  it('describes the purpose in the words the person saw', () => {
    const rows = presentConsentHistory(receipts, now).rows;
    expect(rows.find((row) => row.purpose === 'share-with-partners')?.wording).toBe(
      'Allow my data to be shared with partners',
    );
  });

  it('says when it was last changed', () => {
    const rows = presentConsentHistory(receipts, now).rows;
    expect(rows.find((row) => row.purpose === 'share-with-partners')?.changed).toBe(
      '7 days ago',
    );
  });

  it('counts how many times a purpose has changed', () => {
    const rows = presentConsentHistory(receipts, now).rows;
    expect(rows.find((row) => row.purpose === 'improve-the-system')?.changes).toBe(2);
  });

  it('puts what is currently allowed first', () => {
    expect(presentConsentHistory(receipts, now).rows[0].purpose).toBe('share-with-partners');
  });

  it('offers to withdraw something currently allowed', () => {
    const rows = presentConsentHistory(receipts, now).rows;
    expect(rows.find((row) => row.granted)?.action).toBe('withdraw');
  });

  it('offers to allow something currently withdrawn', () => {
    const rows = presentConsentHistory(receipts, now).rows;
    expect(rows.find((row) => !row.granted)?.action).toBe('allow');
  });

  it('says how many things are currently allowed', () => {
    expect(presentConsentHistory(receipts, now).summary).toBe('1 of 2 allowed');
  });

  it('says plainly when nothing has ever been asked', () => {
    expect(presentConsentHistory([], now).summary).toBe('Nothing has been asked of you yet');
  });

  it('shows no rows when there is no history', () => {
    expect(presentConsentHistory([], now).rows).toEqual([]);
  });

  it('keeps the full history available per purpose', () => {
    const rows = presentConsentHistory(receipts, now).rows;
    const row = rows.find((item) => item.purpose === 'improve-the-system');
    expect(row?.history.map((entry) => entry.receiptId)).toEqual(['r2', 'r1']);
  });

  it('shows the history newest first', () => {
    const rows = presentConsentHistory(receipts, now).rows;
    const row = rows.find((item) => item.purpose === 'improve-the-system');
    expect(row?.history[0].granted).toBe(false);
  });
});
