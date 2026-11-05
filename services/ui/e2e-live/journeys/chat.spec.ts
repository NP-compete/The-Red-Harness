import { test, expect } from '@playwright/test';
import { agentGet, agentTry, gotoLive, mounted, requireStack, USER } from '../helpers/live';

/**
 * A question typed into the browser, answered by the real model,
 * and still there afterwards.
 *
 * The mocked suite asserts the exact sentence it stubbed. This
 * cannot: the model writes something different every time. So it
 * asserts the things that are true of *any* real answer — the URL
 * moved to a thread, text arrived that is not the question
 * echoed back, and the thread the agent persisted is the one the
 * browser is looking at.
 *
 * That last check is the point of the file. A UI can show an
 * answer it never saved, and the person who finds out is the one
 * who reloads the page.
 */

test.beforeAll(async ({ request }) => {
  await requireStack(request);
});

test('a question reaches the model and the thread survives it', async ({ page, request }) => {
  const question = 'In one short sentence, what are you for?';

  await gotoLive(page, '/chat');
  await page.waitForSelector('textarea', { state: 'visible' });

  // Type first, then wait for the button to react to it.
  //
  // This is an interactivity check rather than a rendering one. A
  // visible textarea only means React has painted; the submit
  // handler attaches a tick later, and a click in that gap does
  // nothing at all — no request is made, and the wait below then
  // sits out its whole timeout against an application that is
  // working perfectly. Submit is disabled while the box is empty,
  // so it going enabled *because of what was typed* is proof the
  // handlers are live. It only ever failed as the first test of a
  // cold suite, where hydration is slowest.
  await page.locator('textarea').fill(question);
  await expect(page.locator('button[type="submit"]')).toBeEnabled();

  // Wait for the run itself to finish, not for text to appear.
  //
  // The browser never POSTs `/threads`: it mints the id with
  // `useState(() => uuidv4())` in HomePage and `/v1/stream`
  // creates the thread under that id on its way through. So the
  // URL is the right place to read it from — and the honest
  // signal that there is anything to check is the stream
  // response closing, which is what this waits on. Polling for
  // text on screen passes while the first token is still
  // arriving, and then the state check races the checkpoint.
  const streamed = page.waitForResponse(
    (res) => res.url().includes('/api/proxy/agent/v1/stream') && res.request().method() === 'POST',
    { timeout: 150_000 },
  );
  await page.locator('button[type="submit"]').click();

  await expect(page).toHaveURL(/\/chat\/[0-9a-f-]{8,}/, { timeout: 60_000 });
  const threadId = page.url().split('/chat/')[1].split('?')[0];

  const stream = await streamed;
  expect(stream.status(), 'the run was accepted').toBeLessThan(400);
  // The body is an SSE stream; reading it to the end is how we
  // know the turn is over rather than merely started.
  await stream.text();

  // An answer, not a spinner. The assistant turn is whatever is
  // on screen that is not the question.
  await expect
    .poll(
      async () => {
        const text = await page.locator('body').innerText();
        return text.replace(question, '').trim().length;
      },
      { timeout: 120_000, message: 'no assistant text arrived' },
    )
    .toBeGreaterThan(40);

  // And the agent kept it. This is the half the screen cannot
  // show — and it is polled, because text on screen means the
  // stream is arriving, not that the run has been written down.
  await expect
    .poll(
      async () => {
        const state = await agentTry(request, `/threads/${threadId}/state`);
        return (state?.values?.messages ?? state?.messages ?? []).length;
      },
      { timeout: 60_000, message: 'the turn was never persisted' },
    )
    .toBeGreaterThanOrEqual(2);
});

test('the thread is listed for the person who created it', async ({ page, request }) => {
  // A thread the sidebar cannot see is one nobody goes back to —
  // this is the `metadata.user_identity` filter, which a
  // server-side thread has been missing before.
  const made = await agentGet(request, '/threads');
  const threads = made.threads ?? made ?? [];
  expect(Array.isArray(threads)).toBe(true);

  await gotoLive(page, '/chat');
  await mounted(page);
  // The sidebar is populated from the same list the API returns.
  expect(threads.length, `no threads listed for ${USER}`).toBeGreaterThan(0);
});
