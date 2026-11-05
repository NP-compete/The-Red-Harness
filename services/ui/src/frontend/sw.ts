/// <reference lib="webworker" />
/**
 * The application shell, so a cold load shows the app.
 *
 * Deliberately thin. Every decision it makes lives in a module that
 * can be read and tested on its own — `strategyFor` decides what to
 * do with a request, `cacheable` decides what may be kept — because
 * a worker is the hardest thing in the product to observe once it
 * is running, and the worst place to discover a rule was wrong.
 *
 * It caches the shell and nothing else. A reply from the API
 * carries conversation content and outlives the session that was
 * allowed to see it.
 */
import { strategyFor } from './lib/sw-strategy';

declare const self: ServiceWorkerGlobalScope;

// Bumping this is what retires the previous cache. The old one is
// deleted on activate rather than left to accumulate across
// releases.
const CACHE = 'shell-v1';

const SHELL = ['/', '/manifest.webmanifest'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      for (const name of await caches.keys()) {
        if (name !== CACHE) await caches.delete(name);
      }
      await self.clients.claim();
    })(),
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const strategy = strategyFor({
    method: request.method,
    url: request.url,
    navigation: request.mode === 'navigate',
  });

  // The common case, and the safe one: the worker does nothing and
  // the request goes to the network as though it were not here.
  if (strategy === 'pass') return;

  if (strategy === 'page') {
    event.respondWith(
      fetch(request).catch(async () => {
        const frame = await caches.match('/');
        // An honest failure rather than a blank frame when even the
        // shell was never cached.
        return frame ?? Response.error();
      }),
    );
    return;
  }

  event.respondWith(
    (async () => {
      const held = await caches.match(request);
      if (held) return held;
      const fresh = await fetch(request);
      // Only a successful reply, and only one from this origin:
      // caching an error would serve it again until the next
      // release.
      if (fresh.ok && fresh.type === 'basic') {
        const cache = await caches.open(CACHE);
        void cache.put(request, fresh.clone());
      }
      return fresh;
    })(),
  );
});

/**
 * Applied only when the page asks.
 *
 * Taking over on its own would swap the application out from under
 * somebody mid-answer.
 */
self.addEventListener('message', (event) => {
  if ((event.data as { type?: string } | null)?.type === 'apply-update') {
    void self.skipWaiting();
  }
});

export {};
