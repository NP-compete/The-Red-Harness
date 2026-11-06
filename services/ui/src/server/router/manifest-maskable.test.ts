import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { getSettings, resetSettings } from '../utils/settings.js';
import { buildManifest } from './manifest.js';

/**
 * Whether the installed icon may be cropped.
 *
 * A platform draws an installed app's icon inside its own shape —
 * a circle, a squircle, a rounded square. There are two ways to
 * hand it one and neither is free:
 *
 * **Declared maskable**, and the platform crops to a safe zone,
 * roughly the middle four fifths. Anything outside is cut off. For
 * a logo drawn with that in mind it looks native; for a wordmark
 * it removes the first and last letters.
 *
 * **Not declared**, and the platform letterboxes it inside a plain
 * background. It looks less polished and all of it survives.
 *
 * Every deployment configures its own logo here and the product
 * cannot see it, so it cannot know which applies. It was declaring
 * maskable for all of them, which trades a cosmetic problem for a
 * destructive one: a letterboxed icon is slightly ugly, a cropped
 * wordmark is the product's name with the ends missing, and
 * nobody who sees it knows the setting that caused it.
 *
 * So the deployment says. A separate field, because the answer is
 * about a specific image rather than a preference — and the
 * default is the one that cannot destroy anything.
 */

describe('the maskable icon', () => {
  beforeEach(() => resetSettings());
  afterEach(() => resetSettings());

  const withBranding = (changes: Record<string, unknown>) => {
    const settings = getSettings();
    Object.assign(settings.branding, changes);
    return buildManifest();
  };

  const purposes = (made: { icons: { purpose?: string; src: string }[] }) =>
    made.icons.map((one) => one.purpose);

  describe('when the deployment has not said its logo is safe to crop', () => {
    it('no icon is declared maskable', () => {
      const made = withBranding({ logo_url: '/logo.png', logo_maskable_url: '' });
      expect(purposes(made)).not.toContain('maskable');
    });

    it('the ordinary icons are still there', () => {
      // Letterboxed is the fallback, not "no icon at all" — an
      // empty list makes the installer substitute a generic one.
      const made = withBranding({ logo_url: '/logo.png', logo_maskable_url: '' });
      expect(made.icons.length).toBeGreaterThanOrEqual(2);
      expect(made.icons.every((one) => one.src === '/logo.png')).toBe(true);
    });

    it('both sizes a browser looks for are declared', () => {
      // Below 192 the install prompt substitutes a generic icon.
      const made = withBranding({ logo_url: '/logo.png', logo_maskable_url: '' });
      const sizes = made.icons.map((one) => one.sizes);
      expect(sizes).toContain('192x192');
      expect(sizes).toContain('512x512');
    });
  });

  describe('when the deployment supplies one drawn for it', () => {
    it('that image is the maskable icon', () => {
      const made = withBranding({
        logo_url: '/logo.png',
        logo_maskable_url: '/logo-maskable.png',
      });
      const maskable = made.icons.find((one) => one.purpose === 'maskable');
      expect(maskable?.src).toBe('/logo-maskable.png');
    });

    it('the ordinary icons still point at the ordinary logo', () => {
      // The two are different images on purpose. Using the
      // padded one everywhere makes the icon small everywhere
      // else it appears.
      const made = withBranding({
        logo_url: '/logo.png',
        logo_maskable_url: '/logo-maskable.png',
      });
      const ordinary = made.icons.filter((one) => one.purpose !== 'maskable');
      expect(ordinary.every((one) => one.src === '/logo.png')).toBe(true);
      expect(ordinary.length).toBeGreaterThanOrEqual(2);
    });

    it('it is declared at the size a mask is cut from', () => {
      const made = withBranding({
        logo_url: '/logo.png',
        logo_maskable_url: '/logo-maskable.png',
      });
      expect(made.icons.find((one) => one.purpose === 'maskable')?.sizes).toBe(
        '512x512',
      );
    });
  });

  describe('a deployment with no logo at all', () => {
    it('declares no icons rather than entries pointing at nothing', () => {
      // Unchanged behaviour, asserted here because the maskable
      // entry is the one most likely to be added back
      // unconditionally by a later edit.
      const made = withBranding({ logo_url: '', logo_maskable_url: '' });
      expect(made.icons).toEqual([]);
    });

    it('a maskable logo alone is still enough to install with', () => {
      // Unusual, but refusing to emit anything because the
      // ordinary field is blank would be a worse surprise than
      // using what was given.
      const made = withBranding({ logo_url: '', logo_maskable_url: '/mask.png' });
      expect(made.icons.some((one) => one.purpose === 'maskable')).toBe(true);
    });
  });

  describe('the check can fail', () => {
    it('declaring maskable is still possible, so the default is a choice', () => {
      // Proof the tests above are not passing because nothing
      // can ever be maskable.
      const made = withBranding({
        logo_url: '/logo.png',
        logo_maskable_url: '/logo-maskable.png',
      });
      expect(purposes(made)).toContain('maskable');
    });
  });
});
