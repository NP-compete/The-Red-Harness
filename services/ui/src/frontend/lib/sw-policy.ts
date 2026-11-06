/**
 * What a service worker is allowed to keep.
 *
 * The worker intercepts every request in its scope, so the question
 * is not which responses are worth caching but which are safe to
 * serve again later — possibly after the session that fetched them
 * has ended, possibly to somebody else at the same machine.
 *
 * The shell is: it is the same bytes for every user and carries
 * nothing about anybody. A reply from the API is not, ever. It
 * carries conversation content and it outlives the session that was
 * allowed to see it.
 *
 * An allowlist rather than a blocklist, and unknown means no. A
 * blocklist has to be right about every path anybody adds later;
 * this one only has to be right about the shell.
 */
const SHELL = [
  /^\/$/,
  /^\/index\.html$/,
  /^\/dist\/frontend\/.+\.(?:js|css|svg|png|jpe?g|webp|woff2?)$/,
  /^\/manifest\.webmanifest$/,
];

/** Paths that must reach the network even though they look static. */
const NEVER = [/^\/api\//, /^\/auth\//];

export function cacheable(url: string): boolean {
  const path = pathOf(url);
  if (path === null) return false;
  // Checked first, so a path under the API that happens to end in
  // `.js` is still the API.
  if (NEVER.some((pattern) => pattern.test(path))) return false;
  return SHELL.some((pattern) => pattern.test(path));
}

/**
 * The path, for something on this origin, or nothing.
 *
 * An absolute URL elsewhere is not ours to cache, and treating one
 * as a path would match a third-party script against the shell
 * patterns.
 */
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
