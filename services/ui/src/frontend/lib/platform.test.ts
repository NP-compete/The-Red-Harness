import { describe, expect, it } from 'vitest';

import { notifiable } from '@/lib/platform';

/**
 * Where a desktop notification is worth asking for.
 *
 * The two failure modes are not symmetric. Offering nothing where it
 * would have worked is a missing feature somebody reports. Asking
 * for permission where delivery is unreliable teaches people that
 * the prompt is noise, and they refuse the next one too.
 *
 * So: unknown is unsupported.
 */
const DESKTOP = ['macOS', 'Windows', 'Linux'];

describe('notifiable', () => {
  describe('what the browser states outright', () => {
    it('allows a listed desktop platform', () => {
      expect(notifiable({ platform: 'macOS' }, DESKTOP)).toBe(true);
    });

    it('allows the others on the list', () => {
      expect(notifiable({ platform: 'Windows' }, DESKTOP)).toBe(true);
      expect(notifiable({ platform: 'Linux' }, DESKTOP)).toBe(true);
    });

    it('refuses a platform the deployment did not list', () => {
      expect(notifiable({ platform: 'Android' }, DESKTOP)).toBe(false);
    });

    it('lets a deployment add one without a code change', () => {
      expect(notifiable({ platform: 'Android' }, [...DESKTOP, 'Android'])).toBe(true);
    });

    it('refuses when the deployment lists nothing', () => {
      expect(notifiable({ platform: 'macOS' }, [])).toBe(false);
    });
  });

  describe('falling back to the user-agent string', () => {
    it('reads macOS from it', () => {
      expect(
        notifiable({ userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)' }, DESKTOP),
      ).toBe(true);
    });

    it('reads Windows from it', () => {
      expect(notifiable({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }, DESKTOP)).toBe(
        true,
      );
    });

    it('reads Linux from it', () => {
      expect(notifiable({ userAgent: 'Mozilla/5.0 (X11; Linux x86_64)' }, DESKTOP)).toBe(true);
    });

    it('does not mistake an iPhone for a desktop', () => {
      expect(
        notifiable({ userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)' }, DESKTOP),
      ).toBe(false);
    });

    it('does not mistake an iPad for a Mac', () => {
      // iPadOS says "Macintosh" in its user agent, which is exactly
      // the trap this has to survive.
      expect(
        notifiable(
          { userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Mobile/15E148' },
          DESKTOP,
        ),
      ).toBe(false);
    });

    it('does not mistake Android for Linux', () => {
      expect(
        notifiable({ userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8)' }, DESKTOP),
      ).toBe(false);
    });

    it('refuses Chrome OS, which is neither', () => {
      expect(
        notifiable({ userAgent: 'Mozilla/5.0 (X11; CrOS x86_64 14541.0.0)' }, DESKTOP),
      ).toBe(false);
    });
  });

  describe('when it cannot tell', () => {
    it('refuses an unparseable string', () => {
      expect(notifiable({ userAgent: 'something else entirely' }, DESKTOP)).toBe(false);
    });

    it('refuses an empty one', () => {
      expect(notifiable({ userAgent: '' }, DESKTOP)).toBe(false);
    });

    it('refuses when the browser says nothing at all', () => {
      expect(notifiable({}, DESKTOP)).toBe(false);
    });
  });

  it('prefers what the browser states to what the string suggests', () => {
    // The string is a guess; `platform` is an answer.
    expect(
      notifiable(
        { platform: 'Android', userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)' },
        DESKTOP,
      ),
    ).toBe(false);
  });
});
