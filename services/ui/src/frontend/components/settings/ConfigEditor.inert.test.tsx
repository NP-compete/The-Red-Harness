import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ConfigEditor } from './ConfigEditor';
import * as api from '../../services/config-editing-api';

/**
 * A section the file does not decide is said so before the save.
 *
 * `agent.yaml` carries four sections — `logging`, `memory`,
 * `platform`, `server` — that nothing reads from the file. The
 * YAML marks each `[env-var]` in a comment, which is invisible
 * to anybody editing through this box: the save is accepted,
 * versioned and reported as drift, and the deployment goes on
 * reading the environment.
 *
 * So the agent reports them on `/config/file` and this renders
 * them. The test that matters is the second one — a notice that
 * appears on every file is a notice people stop reading.
 */

const EDITING = {
  mode: 'readwrite',
  editable: true,
  paths: ['config/agent/runtime/agent.yaml'],
  store: 'postgres',
  durable: true,
};

const TREE = {
  root: '/app/config/agent',
  mode: 'readwrite',
  files: [{ path: 'config/agent/runtime/agent.yaml', bytes: 10, editable: true }],
  total: 1,
  editable: 1,
  why_not_all: '',
};

function answering(inert: { section: string; decided_by: string }[]) {
  vi.spyOn(api, 'readEditingState').mockResolvedValue(EDITING as never);
  vi.spyOn(api, 'readConfigTree').mockResolvedValue(TREE as never);
  vi.spyOn(api, 'readConfigFile').mockResolvedValue({
    path: 'config/agent/runtime/agent.yaml',
    content: 'name: Example\n',
    exists: true,
    version: 0,
    inert,
  } as never);
}

describe('ConfigEditor, sections the file does not decide', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('names them, and what decides instead', async () => {
    answering([
      { section: 'platform', decided_by: 'PLATFORM_AUDIT_ENABLED decides' },
    ]);
    render(<ConfigEditor />);

    const note = await screen.findByRole('note');
    expect(note).toHaveTextContent('platform');
    // The point is not that something is wrong — it is where to
    // go instead. A notice that said only "this does nothing"
    // would leave somebody with no next step.
    expect(note).toHaveTextContent('PLATFORM_AUDIT_ENABLED');
  });

  it('says nothing about a file that decides everything in it', async () => {
    answering([]);
    render(<ConfigEditor />);

    // Waited for rather than asserted immediately: the file
    // loads asynchronously, and a synchronous check would pass
    // before the notice had a chance to appear.
    await screen.findByRole('textbox');
    await waitFor(() =>
      expect(screen.queryByRole('note')).not.toBeInTheDocument(),
    );
  });
});
