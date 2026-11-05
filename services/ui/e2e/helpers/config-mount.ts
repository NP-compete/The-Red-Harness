import type { Page } from '@playwright/test';

export interface BrandingColors {
  primary: string;
  accent: string;
  background: string;
  foreground: string;
}

export interface BrandingOverride {
  title?: string;
  logo_url?: string;
  favicon_url?: string;
  colors?: {
    light?: Partial<BrandingColors>;
    dark?: Partial<BrandingColors>;
  };
}

export interface FeaturesOverride {
  debug_mode_default?: boolean;
  auth_enabled?: boolean;
  memory_enabled?: boolean;
}

const DEFAULT_LIGHT: BrandingColors = {
  primary: '#0066cc',
  accent: '#a60000',
  background: '#ffffff',
  foreground: '#1a1a1a',
};

const DEFAULT_DARK: BrandingColors = {
  primary: '#4dabf7',
  accent: '#f56e6e',
  background: '#0a1628',
  foreground: '#f0f4f8',
};

/**
 * Mock config and agent-proxy endpoints so tests do not depend on a real
 * agent backend. Config endpoints could be served by the real Fastify process
 * but overriding them keeps tests hermetic.
 *
 * @param branding  Branding values to use (merged with defaults).
 * @param features  Feature flags to use (merged with defaults).
 * @param agentHealth  Agent health status — one of 'healthy', 'unhealthy', or 'unknown'.
 */
export async function mountConfig(
  page: Page,
  branding: BrandingOverride = {},
  features: FeaturesOverride = {},
  agentHealth: 'healthy' | 'unhealthy' | 'unknown' = 'healthy',
): Promise<void> {
  // The very first route registered, so everything after it wins
  // — Playwright tries the most recently registered route, not
  // the most specific. Every spec calls this helper before
  // registering its own mocks, so each of those still takes
  // precedence.
  //
  // Anything left over is answered here rather than allowed to
  // travel. There is no agent in these runs, so an unmocked call
  // reaches the proxy, which waits on a host that is not
  // listening. That wait accumulates: this suite runs on one
  // worker, and the same accessibility file that passes 22 of 22
  // alone loses its last cases when it runs after sixty others.
  //
  // 503, not an empty body: these endpoints return different
  // shapes, and a panel handed the wrong one renders something
  // stranger than a panel told the agent is away. "Away" is a
  // state they are all built for, and it arrives at once.
  await page.route('**/api/proxy/agent/**', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'no agent in this test run' }),
    }),
  );

  await page.route('**/api/config/branding', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        logo_url: branding.logo_url ?? '',
        title: branding.title ?? 'Test Agent',
        ...(branding.favicon_url ? { favicon_url: branding.favicon_url } : {}),
        colors: {
          light: { ...DEFAULT_LIGHT, ...branding.colors?.light },
          dark: { ...DEFAULT_DARK, ...branding.colors?.dark },
        },
      }),
    }),
  );

  await page.route('**/api/config/features', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        debug_mode_default: features.debug_mode_default ?? false,
        auth_enabled: features.auth_enabled ?? false,
        memory_enabled: features.memory_enabled ?? true,
      }),
    }),
  );

  await page.route('**/api/proxy/agent/threads/*/feedback**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  );

  await page.route('**/api/announcement', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ enabled: false }),
    }),
  );

  const healthHttpStatus = agentHealth === 'healthy' ? 200 : 503;
  await page.route('**/api/health/agent', (route) =>
    route.fulfill({
      status: healthHttpStatus,
      contentType: 'application/json',
      body: JSON.stringify({ status: agentHealth }),
    }),
  );

  await page.route('**/api/proxy/agent/threads/search', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: '[]',
    }),
  );

  await page.route('**/api/proxy/agent/mcp/oauth/connections', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ connections: [] }),
    }),
  );

  // The server list, so the MCP panel has something to render.
  // Without it the fallback above answers 503 and the panel shows
  // its error state — a different page from the one the tests
  // about this panel are asking after.
  await page.route('**/api/proxy/agent/mcp/servers', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        servers: [
          {
            name: 'jira',
            url: 'https://mcp.example.test/mcp',
            display_name: 'Jira',
            description: 'Issues and boards.',
            has_icon: false,
            transport: 'streamable_http',
            enabled: true,
            auth_mode: 'dcr',
            credential: 'not needed',
            tool_prefix: 'jira',
          },
        ],
        dcr_enabled: true,
      }),
    }),
  );

  await page.route('**/api/proxy/agent/personalization/memories', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: '[]',
    }),
  );
}

/** Minimal config: only required fields populated, no logo, default colors. */
export async function mountMinimalConfig(page: Page): Promise<void> {
  return mountConfig(page, { title: 'Minimal Agent' });
}

/** Full config: all optional fields populated, custom primary colour. */
export async function mountFullConfig(page: Page): Promise<void> {
  return mountConfig(
    page,
    {
      title: 'Full Config Agent',
      logo_url: '/dist/frontend/redhat-logo.svg',
      favicon_url: '/dist/frontend/redhat-logo.svg',
      colors: {
        light: { primary: '#cc0000', accent: '#006600', background: '#f5f5f5', foreground: '#111111' },
        dark: { primary: '#ff6666', accent: '#66cc66', background: '#1a1a2e', foreground: '#e0e0e0' },
      },
    },
    { debug_mode_default: false, auth_enabled: false },
  );
}
