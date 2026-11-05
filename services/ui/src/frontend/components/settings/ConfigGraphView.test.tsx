import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ConfigGraphView } from './ConfigGraphView';

/**
 * E34 in the product.
 *
 * The diagram's whole reason to exist is the dangling reference: a
 * subagent naming a skill that no longer exists is the one thing six
 * YAML files cannot show an author. So that is what is asserted
 * hardest here, along with the two states that are easy to conflate —
 * "not asked yet" and "the agent cannot say" — because drawing the
 * second as the first leaves a spinner on screen for ever.
 */

const GRAPH = {
  root: '/config/agent',
  nodes: [
    { id: 'agent:root', kind: 'agent', label: 'Workpilot', path: 'runtime/agent.yaml' },
    { id: 'subagent:curator', kind: 'subagent', label: 'curator', path: 'subagents/curator.md' },
    { id: 'skill:gone', kind: 'skill', label: 'gone', path: null, missing: true },
  ],
  edges: [
    { from: 'agent:root', to: 'subagent:curator', kind: 'delegates-to', broken: null },
    {
      from: 'subagent:curator',
      to: 'skill:gone',
      kind: 'uses-skill',
      broken: "no skill named 'gone' in skills/",
    },
  ],
  problems: [{ where: 'subagent:curator', what: "no skill named 'gone' in skills/" }],
  element_types: ['agent', 'skill', 'subagent'],
  counts: { agent: 1, skill: 1, subagent: 1 },
};

function serve(body: unknown | null) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      body === null
        ? { ok: false, status: 404, json: async () => ({}) }
        : { ok: true, status: 200, json: async () => body },
    ),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('ConfigGraphView', () => {
  it('draws what the tree contains, counted by the agent', async () => {
    serve(GRAPH);
    render(<ConfigGraphView onOpenFile={() => {}} />);
    expect(await screen.findByText('Workpilot')).toBeInTheDocument();
    expect(screen.getByText(/1 agent · 1 skill · 1 subagent/)).toBeInTheDocument();
  });

  it('says why a reference does not resolve', async () => {
    serve(GRAPH);
    render(<ConfigGraphView onOpenFile={() => {}} />);
    expect(await screen.findByText(/no skill named 'gone'/)).toBeInTheDocument();
  });

  it('opens the file a box came from', async () => {
    const opened: string[] = [];
    serve(GRAPH);
    render(<ConfigGraphView onOpenFile={(p) => opened.push(p)} />);
    await userEvent.click(await screen.findByText('curator'));
    expect(opened).toEqual(['subagents/curator.md']);
  });

  it('cannot open a box nothing declares', async () => {
    serve(GRAPH);
    render(<ConfigGraphView onOpenFile={() => {}} />);
    await waitFor(() => expect(screen.getByText('gone')).toBeInTheDocument());
    expect(screen.getByText('gone').closest('button')).toBeDisabled();
  });

  it('an agent that cannot draw its configuration says so', async () => {
    /** Rather than a spinner that never resolves. */
    serve(null);
    render(<ConfigGraphView onOpenFile={() => {}} />);
    expect(await screen.findByText(/cannot draw its configuration/)).toBeInTheDocument();
  });
});

describe('ConfigGraphView editing (E34-T3)', () => {
  function serveMany(handler: (url: string, init?: RequestInit) => unknown) {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        const body = handler(url, init);
        if (body === undefined) {
          return { ok: false, status: 422, json: async () => ({ message: 'no' }) };
        }
        return { ok: true, status: 200, json: async () => body };
      }),
    );
  }

  const SUBAGENT_GRAPH = {
    ...GRAPH,
    nodes: [
      {
        id: 'subagent:curator',
        kind: 'subagent',
        label: 'curator',
        path: 'subagents/curator.md',
        model: 'old-model',
      },
    ],
    edges: [],
    problems: [],
    element_types: ['subagent'],
    counts: { subagent: 1 },
  };

  async function pickCurator(handler: (url: string, init?: RequestInit) => unknown) {
    serveMany(handler);
    render(<ConfigGraphView onOpenFile={() => {}} />);
    await userEvent.click(await screen.findByText('curator'));
  }

  it('shows the change before writing it', async () => {
    const calls: string[] = [];
    await pickCurator((url, init) => {
      calls.push(`${init?.method ?? 'GET'} ${url}`);
      if (url.includes('/graph/edit')) {
        return { path: 'config/agent/subagents/curator.md', content: 'model: new\n', written: false };
      }
      return SUBAGENT_GRAPH;
    });

    await userEvent.click(screen.getByText('Show what would change'));
    expect(await screen.findByText(/would be written to/)).toBeInTheDocument();
    // Nothing was written: the only write-shaped call is the preview.
    expect(calls.filter((c) => c.startsWith('POST')).length).toBe(1);
  });

  it('writes only on a second, explicit press', async () => {
    const bodies: string[] = [];
    await pickCurator((url, init) => {
      if (init?.body) bodies.push(String(init.body));
      if (url.includes('/graph/edit')) {
        return { path: 'config/agent/subagents/curator.md', content: 'model: new\n', written: !JSON.parse(String(init?.body)).preview };
      }
      if (url.includes('/config/file')) {
        return { content: 'x', exists: true, version: 4 };
      }
      return SUBAGENT_GRAPH;
    });

    await userEvent.click(screen.getByText('Show what would change'));
    await userEvent.click(await screen.findByText('Save this change'));

    const written = bodies.map((b) => JSON.parse(b)).filter((b) => b.preview === false);
    expect(written).toHaveLength(1);
    // The version read at save time, not at preview time.
    expect(written[0].base_version).toBe(4);
  });

  it('shows the agent’s own sentence when it refuses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) =>
        url.includes('/graph/edit')
          ? {
              ok: false,
              status: 422,
              json: async () => ({ message: 'a list would lose the comments around it' }),
            }
          : { ok: true, status: 200, json: async () => SUBAGENT_GRAPH },
      ),
    );
    render(<ConfigGraphView onOpenFile={() => {}} />);
    await userEvent.click(await screen.findByText('curator'));
    await userEvent.click(screen.getByText('Show what would change'));
    expect(await screen.findByText(/lose the comments/)).toBeInTheDocument();
  });
});
