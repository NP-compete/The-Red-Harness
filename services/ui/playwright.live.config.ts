import { defineConfig, devices } from '@playwright/test';

/**
 * End to end against a stack that is actually running.
 *
 * `playwright.config.ts` is the other kind of test and both are
 * wanted: it starts its own BFF, points it at a port with nothing
 * behind it, and mocks every agent reply. That makes it fast,
 * hermetic and able to assert exact strings — and it means a
 * green run proves nothing about the agent, the database, the
 * scheduler or the proxy, because none of them were there.
 *
 * This config starts nothing. It drives the deployed stack
 * through the ingress: browser, BFF, agent, Postgres, Redis. The
 * assertions are correspondingly looser — a real model does not
 * say the same sentence twice, so these check that an answer
 * arrived and that it landed where the product says it lands,
 * never that it contains a particular phrase.
 *
 *     make e2e-live
 *
 * `ui.localhost` resolves to 127.0.0.1, so the browser reaches
 * the ingress by name and the Host-based routing works without
 * any header rewriting — which a browser would not allow anyway.
 */
const BASE = process.env.E2E_LIVE_BASE_URL ?? 'http://ui.localhost:8081';

export default defineConfig({
  testDir: './e2e-live',
  // A real model answers in seconds, not milliseconds, and one of
  // these waits for a scheduling round trip.
  timeout: 180_000,
  expect: { timeout: 30_000 },
  // Serial. These share one deployment and one database: two
  // workers creating and deleting threads at once makes each
  // other's list assertions flaky for reasons that have nothing
  // to do with the product.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report-live' }]],
  use: {
    baseURL: BASE,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    serviceWorkers: 'block',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
