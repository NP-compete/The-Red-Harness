import { cacheable } from './sw-policy';

export type Strategy = 'pass' | 'shell' | 'page';

/** Paths the worker must never answer from anywhere but the network. */
const NEVER = /^\/(?:api|auth)\//;

/**
 * What the worker should do with a request it intercepted.
 *
 * `pass` is the default and the safe one: the worker gets out of
 * the way. `shell` may come from the cache. `page` answers a
 * navigation with the cached application frame, which is what makes
 * an offline load show the app rather than the browser's error
 * page.
 *
 * Reads only. A POST or a DELETE has an effect, and serving one
 * from a cache either repeats the effect or hides that it never
 * happened — both worse than failing honestly.
 */
export function strategyFor({
  method,
  url,
  navigation = false,
}: {
  method: string;
  url: string;
  navigation?: boolean;
}): Strategy {
  if (method !== 'GET') return 'pass';

  const path = pathOf(url);
  if (path === null) return 'pass';
  // Checked before the navigation case: a sign-in redirect served
  // from a cache is a sign-in that silently does nothing.
  if (NEVER.test(path)) return 'pass';

  // Every route renders from the same HTML, so a route the cache
  // has never seen is not a miss.
  if (navigation) return 'page';

  return cacheable(path) ? 'shell' : 'pass';
}

function pathOf(url: string): string | null {
  if (url.startsWith('/')) return url.split('?')[0];
  try {
    const parsed = new URL(url);
    if (typeof location !== 'undefined' && parsed.origin !== location.origin) return null;
    return parsed.pathname;
  } catch {
    return null;
  }
}
