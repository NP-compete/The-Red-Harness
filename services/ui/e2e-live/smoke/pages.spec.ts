import { test, expect } from '@playwright/test';
import { gotoLive, mounted, requireStack } from '../helpers/live';

/**
 * Every page the product routes to, loaded against the real
 * stack.
 *
 * This is the cheapest test in the suite and the one that catches
 * the most: a page that renders here has got its bundle, its
 * config, its BFF call and whatever the agent answers, all of
 * which the mocked suite replaces. A chunk that fails to load
 * only in a built image shows up as a blank page, and only here.
 */

const PAGES = [
  ['/chat', 'chat'],
  ['/projects', 'projects'],
  ['/spaces', 'spaces'],
  ['/scheduled', 'scheduled'],
  ['/settings', 'settings'],
  ['/analytics', 'analytics'],
  ['/admin', 'admin'],
] as const;

test.beforeAll(async ({ request }) => {
  await requireStack(request);
});

for (const [path, name] of PAGES) {
  test(`${name} renders`, async ({ page }) => {
    const errors: string[] = [];
    // A page that renders a shell and throws underneath looks
    // fine in a screenshot, so the console is part of the
    // assertion rather than a debugging aid.
    page.on('pageerror', (error) => errors.push(error.message));

    const response = await gotoLive(page, path);
    expect(response?.status(), `${path} responded`).toBeLessThan(400);
    await mounted(page);

    expect(errors, `${path} threw in the browser`).toEqual([]);
  });
}

test('an unknown route does not blank the application', async ({ page }) => {
  // The SPA serves index.html for everything, so a wrong URL has
  // to land somewhere a person can act on rather than on nothing.
  //
  // Every response is recorded from before the navigation, so a
  // failure can say what the server actually answered. Attaching
  // the listener inside the wait is too late: the document's own
  // response has already been and gone, which is how a throttled
  // page first showed up here as a bare "element(s) not found".
  const answers: string[] = [];
  page.on('response', (res) => {
    if (res.status() >= 400) answers.push(`${res.status()} ${res.url()}`);
  });

  const response = await gotoLive(page, '/this-route-does-not-exist');
  const shell = page.locator('#main-content, main, [role="main"]').first();
  await expect(
    shell,
    `document was ${response?.status()}; failures: ${answers.slice(0, 5).join(', ') || 'none'}`,
  ).toBeVisible();
});
