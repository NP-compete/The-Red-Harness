import { describe, expect, it } from 'vitest';

import { presentNumericCheck } from '@/lib/numeric-check-view';

describe('presentNumericCheck', () => {
  it('says nothing when every figure held up', () => {
    expect(presentNumericCheck({ checked: 2, unsupported: [] })).toBeNull();
  });

  it('says nothing when there were no figures to check', () => {
    expect(presentNumericCheck({ checked: 0, unsupported: [] })).toBeNull();
  });

  it('names a figure that appears nowhere in the sources', () => {
    const result = presentNumericCheck({ checked: 2, unsupported: ['750'] });
    expect(result?.warning).toBe('750 does not appear in any source');
  });

  it('names several such figures', () => {
    const result = presentNumericCheck({ checked: 3, unsupported: ['750', '900'] });
    expect(result?.warning).toBe('750, 900 do not appear in any source');
  });

  it('lists the figures so each can be looked at', () => {
    const result = presentNumericCheck({ checked: 3, unsupported: ['750', '900'] });
    expect(result?.figures).toEqual(['750', '900']);
  });

  it('says how much of the answer was checked', () => {
    const result = presentNumericCheck({ checked: 3, unsupported: ['750'] });
    expect(result?.detail).toBe('1 of 3 figures could not be traced');
  });

  it('treats an untraceable figure as worth noticing', () => {
    const result = presentNumericCheck({ checked: 2, unsupported: ['750'] });
    expect(result?.severity).toBe('medium');
  });

  it('treats an answer that is all untraceable figures as worse', () => {
    const result = presentNumericCheck({ checked: 2, unsupported: ['750', '900'] });
    expect(result?.severity).toBe('high');
  });
});
