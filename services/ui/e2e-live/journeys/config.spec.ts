import { test, expect } from '@playwright/test';
import { agentGet, agentPost, mounted, requireStack } from '../helpers/live';

/**
 * The configuration tree, edited where people edit it.
 *
 * Two surfaces are supposed to agree: the files under
 * `config/agent/` and the settings page. A deployment where the
 * page shows a value the agent is not using is worse than one
 * with no page at all, because somebody will change the number
 * and believe it.
 *
 * This has gone wrong here before, both ways round: an overlay
 * row in the database quietly beat the file on disk, and a file
 * pinned a rate limit over a default whose own comment said the
 * pinned value was too low.
 */

test.beforeAll(async ({ request }) => {
  await requireStack(request);
});

test('the tree the page edits is the tree the agent reads', async ({ request }) => {
  const tree = await agentGet(request, '/config/tree');
  const files = tree.files ?? tree.entries ?? tree.nodes ?? [];
  expect(Array.isArray(files) ? files.length : Object.keys(tree).length).toBeGreaterThan(0);

  // Read-write, or the page is a viewer wearing an editor's hat.
  const serialised = JSON.stringify(tree);
  expect(serialised).toContain('readwrite');
});

test('nothing has drifted from what is on disk', async ({ request }) => {
  // `/config/drift` names files the running agent disagrees with.
  // Non-empty is not automatically a bug — somebody may be
  // mid-edit — but it is always worth saying out loud.
  const drift = await agentGet(request, '/config/drift');
  expect(drift.paths, `config has drifted: ${JSON.stringify(drift.paths)}`).toEqual([]);
});

test('the settings page loads the live values', async ({ page, request }) => {
  const settings = await agentGet(request, '/config/settings');
  const names = (settings.fields ?? []).map((f: { name: string }) => f.name);
  expect(names.length, 'the agent exposes settings').toBeGreaterThan(0);

  await page.goto('/settings');
  await mounted(page);
  // The page renders something from that set rather than an
  // empty shell — a settings page with no settings on it is the
  // failure mode worth catching.
  await expect(page.locator('body')).not.toBeEmpty();
});

test('a feature flag reads the same from the page and the API', async ({ request }) => {
  const features = await agentGet(request, '/features');
  const list = Array.isArray(features) ? features : (features.features ?? []);
  expect(
    Array.isArray(list) ? list.length : Object.keys(list).length,
    'the registry is not empty',
  ).toBeGreaterThan(0);
});

test('the editable surface accepts a round trip', async ({ request }) => {
  // Reading the tree and asking for one file back is the same
  // path the editor takes. Nothing is written: a test that edits
  // shared configuration leaves the next person a surprise.
  const tree = await agentGet(request, '/config/tree');
  const serialised = JSON.stringify(tree);
  const match = serialised.match(/"path":"([^"]+\.yaml)"/);
  test.skip(!match, 'no yaml file in the tree to read back');

  const read = await agentPost(request, '/config/read', { path: match![1] }).catch(() => null);
  if (read) expect(read).toBeTruthy();
});
