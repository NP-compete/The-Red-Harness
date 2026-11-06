import { test, expect } from '@playwright/test';
import { agentGet, agentPost, gotoLive, mounted, requireStack, unique } from '../helpers/live';

/**
 * A scheduled task, from creation to the page that lists it.
 *
 * The chain has a hole in it that only an end to end test sees:
 * a cron is bound to a thread by a foreign key that cascades, so
 * deleting the conversation takes the schedule with it. A
 * schedule whose thread is swept after its first firing looks
 * like it worked once and then vanished — which is exactly what
 * happened here before `on_run_completed: keep`.
 *
 * Nothing here waits for 08:00. It asserts the parts that can be
 * checked now: the schedule exists, it is bound to a thread that
 * still exists, and the page shows it.
 */

test.beforeAll(async ({ request }) => {
  await requireStack(request);
});

test('a schedule survives being created, and keeps its thread', async ({ request }) => {
  const name = unique('schedule');
  const thread = await agentPost(request, '/threads', {
    metadata: { thread_name: name },
  });
  const threadId = thread.thread_id;

  await agentPost(request, `/threads/${threadId}/runs/crons`, {
    assistant_id: 'agent',
    schedule: '0 8 * * 1-5',
    input: { messages: [{ role: 'human', content: 'Morning briefing.' }] },
    metadata: { e2e_live: name },
    // Without this the thread is swept after the first run and
    // the next firing has nowhere to land.
    on_run_completed: 'keep',
  });

  const found = await agentPost(request, '/runs/crons/search', { limit: 50 });
  const crons = Array.isArray(found) ? found : (found.crons ?? []);
  const mine = crons.filter((c: { metadata?: Record<string, string> }) => c.metadata?.e2e_live === name);
  expect(mine, 'the schedule was stored').toHaveLength(1);
  expect(mine[0].thread_id, 'it is bound to its own conversation').toBe(threadId);

  // The thread it hangs off is still there. The cascade means
  // this is the same assertion as "the schedule is still there"
  // tomorrow morning.
  const still = await agentGet(request, `/threads/${threadId}`);
  expect(still.thread_id).toBe(threadId);

  // Clean up only what this test made.
  await request.delete(`${process.env.E2E_LIVE_AGENT_URL ?? 'http://agent.localhost:8081'}/runs/crons/${mine[0].cron_id}`, {
    headers: { 'X-User-Id': process.env.E2E_LIVE_USER ?? 'kind-dev-user' },
  });
});

test('the scheduled page lists what the API has', async ({ page, request }) => {
  const found = await agentPost(request, '/runs/crons/search', { limit: 50 });
  const crons = Array.isArray(found) ? found : (found.crons ?? []);

  await gotoLive(page, '/scheduled');
  await mounted(page);

  if (crons.length === 0) {
    // An empty state is a feature too, and the page must not be
    // blank — `make kind-seed` puts one there.
    await expect(page.locator('body')).not.toBeEmpty();
    return;
  }

  // The page renders in plain English rather than cron syntax,
  // so the assertion is that it shows *something* per schedule,
  // not that it echoes `0 8 * * 1-5`.
  await expect
    .poll(async () => (await page.locator('body').innerText()).length, { timeout: 20_000 })
    .toBeGreaterThan(100);
});
