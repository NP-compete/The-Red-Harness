import { describe, expect, it } from 'vitest';

import { presentRecipientCheck } from '@/lib/recipient-check-view';

const quiet = {
  reaches: 1,
  outside: [] as string[],
  unfamiliar: [] as string[],
  reasons: [] as string[],
};

describe('presentRecipientCheck', () => {
  it('says nothing about an ordinary message to a colleague', () => {
    expect(presentRecipientCheck(quiet)).toBeNull();
  });

  it('says how many people a message would reach', () => {
    const broad = { ...quiet, reaches: 401, reasons: ['a mailing list'] };
    expect(presentRecipientCheck(broad)?.headline).toBe('This would reach 401 people');
  });

  it('counts a single person properly', () => {
    const outsider = {
      ...quiet,
      outside: ['kai@outside.example'],
      reasons: ['someone outside the organisation'],
    };
    expect(presentRecipientCheck(outsider)?.headline).toBe('This would reach 1 person');
  });

  it('gives every reason it is asking', () => {
    const both = {
      ...quiet,
      outside: ['kai@outside.example'],
      unfamiliar: ['kai@outside.example'],
      reasons: ['someone outside the organisation', 'an address not written to before'],
    };
    expect(presentRecipientCheck(both)?.reasons).toEqual([
      'someone outside the organisation',
      'an address not written to before',
    ]);
  });

  it('names addresses outside the organisation', () => {
    const outsider = {
      ...quiet,
      outside: ['kai@outside.example'],
      reasons: ['someone outside the organisation'],
    };
    expect(presentRecipientCheck(outsider)?.highlight).toEqual(['kai@outside.example']);
  });

  it('names an unfamiliar address too', () => {
    const stranger = {
      ...quiet,
      unfamiliar: ['new@inside.example'],
      reasons: ['an address not written to before'],
    };
    expect(presentRecipientCheck(stranger)?.highlight).toEqual(['new@inside.example']);
  });

  it('names an address that is both only once', () => {
    const both = {
      ...quiet,
      outside: ['kai@outside.example'],
      unfamiliar: ['kai@outside.example'],
      reasons: ['someone outside the organisation'],
    };
    expect(presentRecipientCheck(both)?.highlight).toEqual(['kai@outside.example']);
  });

  it('makes sending the deliberate choice', () => {
    const broad = { ...quiet, reaches: 401, reasons: ['a mailing list'] };
    expect(presentRecipientCheck(broad)?.actions).toEqual(['Send', 'Edit recipients', 'Cancel']);
  });

  it('waits rather than sending while it asks', () => {
    const broad = { ...quiet, reaches: 401, reasons: ['a mailing list'] };
    expect(presentRecipientCheck(broad)?.blocking).toBe(true);
  });

  it('treats reaching a crowd as worth real attention', () => {
    const broad = { ...quiet, reaches: 401, reasons: ['a mailing list'] };
    expect(presentRecipientCheck(broad)?.severity).toBe('high');
  });

  it('treats one unfamiliar colleague as a lighter ask', () => {
    const stranger = {
      ...quiet,
      unfamiliar: ['new@inside.example'],
      reasons: ['an address not written to before'],
    };
    expect(presentRecipientCheck(stranger)?.severity).toBe('medium');
  });
});
