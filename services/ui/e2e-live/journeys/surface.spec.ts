import { test, expect } from '@playwright/test';
import { agentGet, agentPost, requireStack } from '../helpers/live';

/**
 * Every feature group answers, in the deployment as built.
 *
 * Not a substitute for the journeys beside this file — a 200
 * says a route is wired, not that the feature works. It is here
 * because the cheap failure is the common one: a router that was
 * not mounted in the image, a capability whose config did not
 * ship, a path that moved. Those are invisible to a unit test
 * and obvious here.
 *
 * `optional` is for capabilities a deployment is allowed to
 * switch off. They answer 404 by design, and counting that as
 * failure would make the suite red on a correct deployment.
 */

type Probe = { path: string; optional?: boolean; post?: unknown };

const SURFACE: Record<string, Probe[]> = {
  health: [{ path: '/healthz' }, { path: '/info' }],
  threads: [{ path: '/threads' }],
  assistants: [{ path: '/assistants' }],
  projects: [{ path: '/projects' }],
  spaces: [{ path: '/spaces' }],
  catalogue: [{ path: '/skills' }, { path: '/subagents' }, { path: '/features' }, { path: '/models' }],
  analytics: [{ path: '/analytics/summary' }, { path: '/analytics/timeseries' }, { path: '/analytics/models' }],
  config: [{ path: '/config/tree' }, { path: '/config/settings' }, { path: '/config/drift' }],
  evals: [{ path: '/evals/status' }, { path: '/evals/checks' }],
  search: [{ path: '/search/threads?q=test' }],
  personalization: [{ path: '/personalization/preferences' }, { path: '/personalization/memories' }],
  mcp: [{ path: '/mcp/servers' }, { path: '/mcp/oauth/connections' }],
  documents: [{ path: '/documents' }, { path: '/knowledge/documents', optional: true }],
  scheduled: [{ path: '/runs/crons/search', post: { limit: 5 } }],
};

test.beforeAll(async ({ request }) => {
  await requireStack(request);
});

for (const [feature, probes] of Object.entries(SURFACE)) {
  test(`${feature} answers`, async ({ request }) => {
    for (const probe of probes) {
      if (probe.post !== undefined) {
        await agentPost(request, probe.path, probe.post);
        continue;
      }
      if (probe.optional) {
        // Reached, or switched off here. Either is a real answer.
        const res = await request.get(
          `${process.env.E2E_LIVE_AGENT_URL ?? 'http://agent.localhost:8081'}${probe.path}`,
          { headers: { 'X-User-Id': process.env.E2E_LIVE_USER ?? 'kind-dev-user' } },
        );
        expect([200, 404], `${probe.path} answered ${res.status()}`).toContain(res.status());
        continue;
      }
      await agentGet(request, probe.path);
    }
  });
}

test('the agent reports which build it is', async ({ request }) => {
  // So a failing run can say which image it was against, rather
  // than leaving somebody to guess whether they tested the fix.
  const info = await agentGet(request, '/info');
  expect(JSON.stringify(info).length).toBeGreaterThan(2);
  console.log(`e2e-live: agent reports ${JSON.stringify(info).slice(0, 200)}`);
});
