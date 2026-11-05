import { describe, expect, it } from 'vitest';

import { presentTranslation } from '@/lib/translation-view';

const asIs = [{ chunk: 'c1', language: 'en', handling: 'as_is' as const, languageUncertain: false }];

describe('presentTranslation', () => {
  it('says nothing when everything was in the asked language', () => {
    expect(presentTranslation(asIs)).toBeNull();
  });

  it('says how many sources were translated', () => {
    const plan = [
      ...asIs,
      { chunk: 'c2', language: 'de', handling: 'translate' as const, languageUncertain: false },
    ];
    expect(presentTranslation(plan)?.note).toBe('1 source was translated from de');
  });

  it('names every language it translated from', () => {
    const plan = [
      { chunk: 'c1', language: 'de', handling: 'translate' as const, languageUncertain: false },
      { chunk: 'c2', language: 'fr', handling: 'translate' as const, languageUncertain: false },
    ];
    expect(presentTranslation(plan)?.note).toBe('2 sources were translated from de, fr');
  });

  it('names a language only once', () => {
    const plan = [
      { chunk: 'c1', language: 'de', handling: 'translate' as const, languageUncertain: false },
      { chunk: 'c2', language: 'de', handling: 'translate' as const, languageUncertain: false },
    ];
    expect(presentTranslation(plan)?.note).toBe('2 sources were translated from de');
  });

  it('warns when something could not be translated', () => {
    const plan = [
      { chunk: 'c1', language: 'de', handling: 'untranslated' as const, languageUncertain: false },
    ];
    expect(presentTranslation(plan)?.warning).toBe('1 source is shown in de, untranslated');
  });

  it('adds no warning when everything translated', () => {
    const plan = [
      { chunk: 'c1', language: 'de', handling: 'translate' as const, languageUncertain: false },
    ];
    expect(presentTranslation(plan)?.warning).toBe('');
  });

  it('treats an untranslated source as worth noticing', () => {
    const plan = [
      { chunk: 'c1', language: 'de', handling: 'untranslated' as const, languageUncertain: false },
    ];
    expect(presentTranslation(plan)?.severity).toBe('low');
  });

  it('treats a clean translation as routine', () => {
    const plan = [
      { chunk: 'c1', language: 'de', handling: 'translate' as const, languageUncertain: false },
    ];
    expect(presentTranslation(plan)?.severity).toBe('info');
  });

  it('lists which sources were translated so they can be checked', () => {
    const plan = [
      ...asIs,
      { chunk: 'c2', language: 'de', handling: 'translate' as const, languageUncertain: false },
    ];
    expect(presentTranslation(plan)?.chunks).toEqual(['c2']);
  });

  it('says nothing about a language it was unsure of', () => {
    const plan = [
      { chunk: 'c1', language: 'de', handling: 'as_is' as const, languageUncertain: true },
    ];
    expect(presentTranslation(plan)).toBeNull();
  });
});
