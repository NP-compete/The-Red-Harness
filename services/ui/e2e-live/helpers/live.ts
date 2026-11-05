import { expect, type APIRequestContext, type Page } from '@playwright/test';

/**
 * Talking to the real agent from a live test.
 *
 * The browser reaches the BFF at `ui.localhost`; the agent is the
 * same ingress under `agent.localhost`. Tests use this to set a
 * fixture up or to check that what the UI did actually reached
 * the database, which is the half a screenshot cannot show.
 */
export const AGENT = process.env.E2E_LIVE_AGENT_URL ?? 'http://agent.localhost:8081';

/** The identity the BFF uses when auth is off, so fixtures land where the UI looks. */
export const USER = process.env.E2E_LIVE_USER ?? 'kind-dev-user';

export async function agentGet(request: APIRequestContext, path: string) {
  const res = await request.get(`${AGENT}${path}`, {
    headers: { 'X-User-Id': USER },
  });
  // The body, not just the code: a 404 from a thread that is not
  // there and a 404 from a capability that is off look identical
  // in a status line.
  expect(res.status(), `GET ${path} -> ${await res.text()}`).toBeLessThan(400);
  return res.json();
}

/**
 * The same call, without the assertion, for polling.
 *
 * A thread row exists before its first checkpoint does, so
 * `/state` answers 404 for a moment after the browser has
 * navigated. Something waiting for that to become true has to be
 * able to see the 404 rather than die on it.
 */
export async function agentTry(request: APIRequestContext, path: string) {
  const res = await request.get(`${AGENT}${path}`, {
    headers: { 'X-User-Id': USER },
  });
  if (res.status() >= 400) return null;
  return res.json();
}

export async function agentPost(request: APIRequestContext, path: string, body: unknown = {}) {
  const res = await request.post(`${AGENT}${path}`, {
    headers: { 'X-User-Id': USER, 'Content-Type': 'application/json' },
    data: body,
  });
  expect(res.status(), `POST ${path}`).toBeLessThan(400);
  return res.json();
}

/**
 * Skip rather than fail when the stack is not up.
 *
 * A suite that cannot tell "the product is broken" from "nobody
 * started it" trains people to ignore it.
 */
export async function requireStack(request: APIRequestContext): Promise<void> {
  const res = await request.get(`${AGENT}/healthz`).catch(() => null);
  if (!res || res.status() >= 400) {
    throw new Error(
      `No stack at ${AGENT}. Start one with \`make kind\`, or point ` +
        `E2E_LIVE_AGENT_URL / E2E_LIVE_BASE_URL at a running deployment.`,
    );
  }
}

/**
 * Navigate, and ride out a throttled window.
 *
 * The BFF limits per client address and a whole pass spends over
 * half of the 600/minute budget — `remaining` was 280 of 600 at
 * the end of one. Two passes inside a window exhaust it, and the
 * second gets a 429 on the document itself, an empty page and no
 * clue why. Proven by printing the navigation's status: the first
 * run passes, the second answers `document was 429`.
 *
 * Waited out rather than hidden. The throttle is correct
 * behaviour by the thing under test, and a suite that cannot be
 * run twice in a minute is a suite people stop running — but a
 * retry that said nothing would turn a real outage into a slow
 * pass, so it is announced and allowed exactly once.
 */
export async function gotoLive(page: Page, path: string) {
  let response = await page.goto(path);
  if (response?.status() === 429) {
    const wait = Number(response.headers()["x-ratelimit-reset"] ?? 60) + 1;
    console.log(
      `e2e-live: ${path} was rate-limited; waiting ${wait}s for the window. ` +
        "Run this suite once a minute, or raise security.rate_limit.max where it runs.",
    );
    await page.waitForTimeout(wait * 1000);
    response = await page.goto(path);
  }
  return response;
}

/**
 * The page has mounted, rather than merely navigated.
 *
 * Throttled responses are watched for and named. The BFF limits
 * per client address, a whole suite spends over half of the
 * 600/minute budget, and two runs inside one window exhaust it —
 * so the last tests of the second run get 429s, no application
 * shell, and a bare "element(s) not found" that says nothing
 * about why. Measured: `remaining` was 280 of 600 at the end of
 * one pass.
 */
export async function mounted(page: Page): Promise<void> {
  const throttled: string[] = [];
  const watch = (res: { status: () => number; url: () => string }) => {
    if (res.status() === 429) throttled.push(res.url());
  };
  page.on('response', watch);
  try {
    await page.waitForLoadState('domcontentloaded');
    await expect(
      page.locator('#main-content, main, [role="main"]').first(),
      throttled.length
        ? `the deployment rate-limited ${throttled.length} request(s) — ` +
          'this suite uses over half the per-minute budget, so two runs ' +
          'in one window throttle the second. Wait a minute, or raise ' +
          'security.rate_limit.max where these run.'
        : 'the application shell never rendered',
    ).toBeVisible();
  } finally {
    page.off('response', watch);
  }
}

/** A name no other run will collide with, so tests can clean up only their own. */
export const unique = (what: string) => `e2e-live ${what} ${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
