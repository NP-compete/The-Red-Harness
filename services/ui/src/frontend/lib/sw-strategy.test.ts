import { describe, expect, it } from 'vitest';

import { strategyFor } from '@/lib/sw-strategy';

/**
 * What the worker does with a request it intercepted.
 *
 * Three answers, and the differences matter. `pass` never touches
 * the cache. `shell` may be served from it. `page` is the one that
 * makes an offline load show the application frame instead of the
 * browser's error page.
 */
describe('strategyFor', () => {
  it('passes an API call straight to the network', () => {
    expect(strategyFor({ method: 'GET', url: '/api/threads/t1' })).toBe('pass');
  });

  it('passes anything that is not a plain read', () => {
    // A POST has an effect. Serving one from a cache would repeat
    // the effect or hide that it never happened.
    expect(strategyFor({ method: 'POST', url: '/dist/frontend/app.js' })).toBe('pass');
  });

  it('passes a DELETE', () => {
    expect(strategyFor({ method: 'DELETE', url: '/dist/frontend/app.js' })).toBe('pass');
  });

  it('serves a script from the shell cache', () => {
    expect(strategyFor({ method: 'GET', url: '/dist/frontend/app.js' })).toBe('shell');
  });

  it('serves the manifest from the shell cache', () => {
    expect(strategyFor({ method: 'GET', url: '/manifest.webmanifest' })).toBe('shell');
  });

  describe('a navigation', () => {
    it('is answered with the application frame', () => {
      expect(
        strategyFor({ method: 'GET', url: '/chat/t1', navigation: true }),
      ).toBe('page');
    });

    it('is answered that way for a route the cache has never seen', () => {
      // Every route renders from the same HTML, so an unvisited one
      // is not a cache miss.
      expect(
        strategyFor({ method: 'GET', url: '/settings/anything', navigation: true }),
      ).toBe('page');
    });

    it('is still passed through when it is an API path', () => {
      expect(
        strategyFor({ method: 'GET', url: '/api/download/report', navigation: true }),
      ).toBe('pass');
    });

    it('is still passed through when it is an auth path', () => {
      // A sign-in redirect served from a cache is a sign-in that
      // silently does nothing.
      expect(
        strategyFor({ method: 'GET', url: '/auth/callback/oidc', navigation: true }),
      ).toBe('pass');
    });
  });

  it('passes anything it does not recognise', () => {
    expect(strategyFor({ method: 'GET', url: '/something/new' })).toBe('pass');
  });

  it('passes a request to another origin', () => {
    expect(
      strategyFor({ method: 'GET', url: 'https://example.com/dist/frontend/app.js' }),
    ).toBe('pass');
  });
});
