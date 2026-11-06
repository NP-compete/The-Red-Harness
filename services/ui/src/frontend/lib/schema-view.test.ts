import { describe, expect, it } from 'vitest';

import { describeSchema } from './schema-view';

const WINDOW = { current: 3, oldestSupported: 2, declared: 3, deprecated: false };

describe('describeSchema', () => {
  it('says which version the configuration declares', () => {
    expect(describeSchema(WINDOW)?.declared).toBe('3');
  });

  it('says which versions the running build reads', () => {
    // The declared version alone is unreadable: two pods on two
    // images read two windows.
    expect(describeSchema(WINDOW)?.accepts).toBe('2–3');
  });

  it('collapses a window of one to a single number', () => {
    const narrow = { ...WINDOW, oldestSupported: 3 };
    expect(describeSchema(narrow)?.accepts).toBe('3');
  });

  it('is not ageing when the configuration is current', () => {
    expect(describeSchema(WINDOW)?.ageing).toBe(false);
  });

  it('is ageing when the configuration is on the old end', () => {
    // The warning somebody needs before the upgrade that removes it.
    const old = { ...WINDOW, declared: 2, deprecated: true };
    expect(describeSchema(old)?.ageing).toBe(true);
  });

  describe('a configuration that declares nothing', () => {
    const absent = { ...WINDOW, declared: null, deprecated: true };

    it('says so rather than showing the version it is read as', () => {
      // "Absent" and "written for version 2" load the same way and
      // are different facts about a tree.
      expect(describeSchema(absent)?.declared).toBe(null);
    });

    it('is still ageing', () => {
      expect(describeSchema(absent)?.ageing).toBe(true);
    });
  });

  describe('an agent that could not say', () => {
    it('reports nothing rather than inventing a version', () => {
      expect(describeSchema(null)).toBe(null);
    });

    it('treats a reply missing the numbers as no answer', () => {
      // An older build that has never heard of the question is not
      // a deployment running version 0.
      expect(describeSchema({ declared: 3 } as never)).toBe(null);
    });
  });
});
