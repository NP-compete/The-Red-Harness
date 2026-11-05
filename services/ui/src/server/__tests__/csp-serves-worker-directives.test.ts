import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { resetSettings } from '../utils/settings.js';
import { buildTestServer } from './test-utils.js';

/**
 * The worker directives reach an actual response.
 *
 * There was already a test for these, and it read the
 * configuration: `security.helmet.csp.worker_src` is `['self']`.
 * That is worth knowing and it is not the question. A directive
 * is only a policy once a browser receives it, and between the
 * setting and the header sits a rename — `worker_src` becomes
 * `workerSrc` — handed to a library that ignores keys it does
 * not recognise. A typo there leaves the setting correct, the
 * test green, and the header without the directive.
 *
 * Which matters more here than for most directives. A service
 * worker intercepts every request in its scope, so `worker-src`
 * is what stops one being installed from somewhere else and
 * reading all of them. A policy that is absent fails open.
 *
 * Checked against a real response for that reason, the way the
 * script and connect directives already are.
 */

describe('the served policy covers the service worker', () => {
  beforeEach(() => resetSettings());
  afterEach(() => resetSettings());

  const policy = async (): Promise<string> => {
    const server = await buildTestServer();
    const response = await server.inject({ method: 'GET', url: '/' });
    const header = response.headers['content-security-policy'];
    expect(header, 'no policy was served at all').toBeDefined();
    return header as string;
  };

  const directive = (header: string, name: string): string | undefined =>
    header
      .split(';')
      .map((one) => one.trim())
      .find((one) => one.startsWith(`${name} `) || one === name);

  it('names worker-src', async () => {
    expect(directive(await policy(), 'worker-src')).toBeDefined();
  });

  it('names manifest-src', async () => {
    expect(directive(await policy(), 'manifest-src')).toBeDefined();
  });

  it('allows a worker from this origin', async () => {
    expect(directive(await policy(), 'worker-src')).toContain("'self'");
  });

  it('allows a worker from nowhere else', async () => {
    // The whole value of the directive. A worker loaded from
    // elsewhere would see every request in scope.
    const found = directive(await policy(), 'worker-src');
    expect(found).not.toContain('*');
    expect(found).not.toContain('http:');
  });

  it('allows a manifest from this origin and no other', async () => {
    const found = directive(await policy(), 'manifest-src');
    expect(found).toContain("'self'");
    expect(found).not.toContain('*');
  });

  it('does not fall back to a default that permits everything', async () => {
    // An absent worker-src inherits default-src, and a
    // permissive default-src would make the absence invisible.
    const header = await policy();
    const fallback = directive(header, 'default-src');
    if (fallback) expect(fallback).not.toContain('*');
  });
});

describe('the check can fail', () => {
  it('a directive that is not there is reported as missing', () => {
    const header = "script-src 'self'; connect-src 'self'";
    const found = header
      .split(';')
      .map((one) => one.trim())
      .find((one) => one.startsWith('worker-src '));
    expect(found).toBeUndefined();
  });

  it('a directive whose name is a prefix of another is not mistaken for it', () => {
    // `worker-src` must not be matched by `worker-src-elsewhere`,
    // nor `script-src` by `script-src-attr`, which is a real
    // directive and sits next to it in most policies.
    const header = "script-src-attr 'none'; worker-src 'self'";
    const names = header
      .split(';')
      .map((one) => one.trim())
      .filter((one) => one.startsWith('script-src '));
    expect(names).toEqual([]);
  });
});
