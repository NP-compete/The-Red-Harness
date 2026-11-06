import { describe, expect, it } from 'vitest';

import { presentLocale } from '@/lib/locale-view';

const locale = {
  language: 'en',
  zone: 'UTC',
  units: 'metric',
  languageFrom: 'workspace' as const,
  switched: false,
  workspaceLanguage: 'en',
};

describe('presentLocale', () => {
  it('says nothing when the reply is in the usual language', () => {
    expect(presentLocale(locale)).toBeNull();
  });

  it('says so when it answered in another language', () => {
    const switched = { ...locale, language: 'fr', languageFrom: 'message' as const, switched: true };
    expect(presentLocale(switched)?.note).toBe('Answering in fr, matching your message');
  });

  it('says where a chosen language came from', () => {
    const chosen = { ...locale, language: 'de', languageFrom: 'setting' as const, switched: true };
    expect(presentLocale(chosen)?.note).toBe('Answering in de, from your settings');
  });

  it('offers a way back to the usual language when it switched on its own', () => {
    const switched = { ...locale, language: 'fr', languageFrom: 'message' as const, switched: true };
    expect(presentLocale(switched)?.action).toBe('Answer in en instead');
  });

  it('offers no way back when the person chose the language themselves', () => {
    const chosen = { ...locale, language: 'de', languageFrom: 'setting' as const, switched: true };
    expect(presentLocale(chosen)?.action).toBe('');
  });

  it('shows the zone times are given in', () => {
    const switched = { ...locale, zone: 'Asia/Tokyo', language: 'fr', languageFrom: 'message' as const, switched: true };
    expect(presentLocale(switched)?.detail).toBe('Times in Asia/Tokyo · metric units');
  });

  it('is a quiet note rather than something to answer', () => {
    const switched = { ...locale, language: 'fr', languageFrom: 'message' as const, switched: true };
    expect(presentLocale(switched)?.dismissible).toBe(true);
  });
});
