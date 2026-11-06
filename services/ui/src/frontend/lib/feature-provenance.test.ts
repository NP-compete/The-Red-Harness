import { describe, expect, it } from 'vitest';

import { whereFrom } from './feature-provenance';

const flag = (over: Record<string, unknown> = {}) => ({
  key: 'auth_enabled',
  scope: 'deployment' as const,
  effect: 'Requires people to sign in.',
  value: false,
  source: 'default' as const,
  overridable: false,
  ...over,
});

describe('whereFrom', () => {
  it('names the environment variable that decided it', () => {
    expect(whereFrom(flag({ source: 'environment', setBy: 'AUTH_ENABLED' }))).toContain(
      'AUTH_ENABLED',
    );
  });

  it('says when the configuration file decided it', () => {
    expect(whereFrom(flag({ source: 'configuration file' }))).toMatch(/configuration file/i);
  });

  it('says when an operator set it here', () => {
    expect(whereFrom(flag({ source: 'set here' }))).toMatch(/set here/i);
  });

  it('says when nobody has touched it', () => {
    expect(whereFrom(flag())).toMatch(/default/i);
  });

  it('copes with an environment source that forgot to say which variable', () => {
    expect(whereFrom(flag({ source: 'environment' }))).toMatch(/outside this deployment/i);
  });
});
