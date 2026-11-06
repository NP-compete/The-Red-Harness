import { describe, expect, it } from 'vitest';

import { cacheable } from '@/lib/sw-policy';

/**
 * What a service worker may keep.
 *
 * The worker intercepts every request in its scope, so the question
 * is not "what is worth caching" but "what is safe to serve again
 * later, possibly to a different session". The shell is. A reply
 * from the API carries conversation content and outlives the
 * session that was allowed to see it.
 */
describe('cacheable', () => {
  describe('the shell, which is the same for everyone', () => {
    it('caches the page itself', () => {
      expect(cacheable('/')).toBe(true);
    });

    it('caches a script', () => {
      expect(cacheable('/dist/frontend/assets/index-abc123.js')).toBe(true);
    });

    it('caches a stylesheet', () => {
      expect(cacheable('/dist/frontend/assets/index-abc123.css')).toBe(true);
    });

    it('caches an icon', () => {
      expect(cacheable('/dist/frontend/workpilot-logo.jpg')).toBe(true);
    });
  });

  describe('anything carrying a conversation', () => {
    it('never caches an API reply', () => {
      expect(cacheable('/api/threads/t1/state')).toBe(false);
    });

    it('never caches one proxied to the agent', () => {
      expect(cacheable('/api/proxy/agent/threads/t1/state')).toBe(false);
    });

    it('never caches a stream', () => {
      expect(cacheable('/api/threads/t1/stream')).toBe(false);
    });

    it('never caches an upload', () => {
      expect(cacheable('/api/uploads/report.pdf')).toBe(false);
    });

    it('is not fooled by a query string', () => {
      expect(cacheable('/api/config/features?v=2')).toBe(false);
    });

    it('is not fooled by something that merely looks like an asset', () => {
      // A path ending `.js` under the API is still the API.
      expect(cacheable('/api/threads/t1/export.js')).toBe(false);
    });
  });

  describe('authentication', () => {
    it('never caches a login or callback', () => {
      expect(cacheable('/auth/callback/oidc')).toBe(false);
    });

    it('never caches a logout', () => {
      expect(cacheable('/auth/logout')).toBe(false);
    });
  });

  it('refuses anything it does not recognise', () => {
    // Unknown is not cached. Caching something nobody thought about
    // is how a private reply ends up served to the next session.
    expect(cacheable('/something/new')).toBe(false);
  });

  it('refuses an absolute URL to somewhere else', () => {
    expect(cacheable('https://example.com/dist/frontend/app.js')).toBe(false);
  });
});
