import { defineConfig, devices } from '@playwright/test';

/**
 * Two or three of these seventy-odd tests fail per whole-suite
 * run, and a different two or three each time. Every one of them
 * passes when its own file is run alone. `retries` covers it on
 * CI; this note is so the next person does not re-walk the parts
 * already measured.
 *
 * The symptom is a page that never renders — a sixty-second
 * timeout waiting for `#main-content` — rather than anything
 * slow or wrong on screen.
 *
 * Ruled out, by measurement rather than reasoning:
 *
 * - **The server.** Polled every eight seconds through a full
 *   run: always 200, slowest response 1.7ms. A page failing to
 *   render while the server answers that URL in a millisecond is
 *   not a server problem.
 * - **Worker count.** One worker and three give the same failure
 *   rate and the same wall time. The duration is bounded by the
 *   accessibility file, whose tests are serial within it.
 * - **Accumulated agent calls.** Fixed, and it did help: see the
 *   fallback in `helpers/config-mount` and `AGENT_TIMEOUT_MS`
 *   below. Together with blocking the shell worker these took
 *   the whole-suite failures from fifteen to about two, which is
 *   where the remaining ones were left.
 *
 * Not yet looked at: the browser process itself, which Playwright
 * reuses across every context in a worker.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: process.env.CI ? 60_000 : 30_000,
  expect: { timeout: process.env.CI ? 15_000 : 10_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:18080',
    trace: 'on-first-retry',
    // The application installs a shell worker. None of these
    // tests are about offline behaviour, and a worker that
    // installs while a page is being measured answers some of
    // that page's requests from its own cache — which is a
    // different page from the one the test asked for.
    serviceWorkers: 'block',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    // Bypasses --env-file=.env (not needed in CI) by invoking the compiled server directly.
    command: 'node dist/server/index.js',
    url: 'http://localhost:18080',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
    // Without these, a server that dies on boot is reported as
    // "timed out waiting 30000ms" and nothing else — the stack
    // trace that says why goes to a pipe nobody reads.
    stdout: 'pipe',
    stderr: 'pipe',
    env: {
      PORT: '18080',
      AUTH_ENABLED: 'false',
      ENVIRONMENT: 'test',
      AGENT_HOST: 'http://localhost:19999',
      // Nothing is listening on that port, deliberately: these
      // tests mock what the agent would say. The default thirty
      // seconds is how long the proxy then holds each call that
      // slipped past a mock, and sixty-odd tests through one
      // server is enough of those to make later pages render
      // after the test waiting for them has given up.
      //
      // One second is longer than anything a reachable host takes
      // and short enough that an unreachable one costs nothing.
      AGENT_TIMEOUT_MS: '1000',
      COOKIE_SIGN: 'playwright-test-secret-32-chars-min-length',
    },
  },
});
