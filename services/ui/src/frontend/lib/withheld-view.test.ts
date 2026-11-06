import { describe, expect, it } from 'vitest';

import { presentWithheld } from '@/lib/withheld-view';

const nothingWithheld = { withheld: 0, requestable: [] as string[], nothingLeft: false };

describe('presentWithheld', () => {
  it('says nothing when the asker could read everything', () => {
    expect(presentWithheld(nothingWithheld)).toBeNull();
  });

  it('says how much was left out', () => {
    const some = { withheld: 2, requestable: [], nothingLeft: false };
    expect(presentWithheld(some)?.note).toBe('2 results you do not have access to were left out');
  });

  it('counts one result in the singular', () => {
    const one = { withheld: 1, requestable: [], nothingLeft: false };
    expect(presentWithheld(one)?.note).toBe('1 result you do not have access to was left out');
  });

  it('names documents the asker is allowed to know about', () => {
    const named = { withheld: 1, requestable: ['handbook'], nothingLeft: false };
    expect(presentWithheld(named)?.documents).toEqual(['handbook']);
  });

  it('names nothing when the asker may not know what exists', () => {
    const hidden = { withheld: 1, requestable: [], nothingLeft: false };
    expect(presentWithheld(hidden)?.documents).toEqual([]);
  });

  it('offers to ask for access to a document it can name', () => {
    const named = { withheld: 1, requestable: ['handbook'], nothingLeft: false };
    expect(presentWithheld(named)?.action).toBe('Request access');
  });

  it('offers nothing to ask for when it can name nothing', () => {
    const hidden = { withheld: 1, requestable: [], nothingLeft: false };
    expect(presentWithheld(hidden)?.action).toBe('');
  });

  it('is blunt when access was the only thing in the way of an answer', () => {
    const blocked = { withheld: 3, requestable: ['handbook'], nothingLeft: true };
    expect(presentWithheld(blocked)?.note).toBe(
      'Everything found for this question is out of your reach',
    );
  });

  it('treats having nothing left as worth noticing', () => {
    const blocked = { withheld: 3, requestable: [], nothingLeft: true };
    expect(presentWithheld(blocked)?.severity).toBe('medium');
  });

  it('treats a partial answer as a quiet note', () => {
    const some = { withheld: 2, requestable: [], nothingLeft: false };
    expect(presentWithheld(some)?.severity).toBe('info');
  });
});
