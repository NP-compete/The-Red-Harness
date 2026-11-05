import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './locales/en.json';

/**
 * Translation setup.
 *
 * English, and only English. The catalogue stays because the
 * alternative is 5,469 strings spread through 94 components, where
 * nobody can find a phrase to change it and nothing stops the same
 * sentence being written three slightly different ways.
 *
 * So this is a string catalogue rather than a translation layer. A
 * key with no string renders as the key, which is ugly and findable
 * — better than blank, which is invisible.
 *
 * There is deliberately no language detection. It only made sense
 * when there was something to detect, and leaving it in would let a
 * stale value in a browser select a language that no longer exists.
 */

/**
 * The languages on offer. One.
 *
 * Kept as a list rather than removed so the shape of "which
 * languages exist" has one answer in one place. Adding a second is
 * then a visible decision — a file, a line here, and the question of
 * who maintains it — rather than something that happens by accident.
 */
export const LANGUAGES = [{ code: 'en', label: 'English' }] as const;

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en } },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: {
    // React escapes already; doing it twice turns an apostrophe in a
    // conversation title into `&#39;`.
    escapeValue: false,
  },
});

export default i18n;
