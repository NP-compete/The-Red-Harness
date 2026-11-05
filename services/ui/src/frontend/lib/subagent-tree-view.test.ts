import { describe, expect, it } from 'vitest';

import { presentSubagentTree } from '@/lib/subagent-tree-view';

const nodes = [
  { id: 'root', name: 'triage', parentId: null as string | null, state: 'running' as const, costs: 0.5 },
  { id: 'a', name: 'researcher', parentId: 'root', state: 'done' as const, costs: 1.0 },
  { id: 'b', name: 'reader', parentId: 'a', state: 'running' as const, costs: 0.25 },
  { id: 'c', name: 'writer', parentId: 'root', state: 'failed' as const, costs: 0.1 },
];

describe('presentSubagentTree', () => {
  it('flattens the tree in reading order', () => {
    expect(presentSubagentTree(nodes).rows.map((r) => r.id)).toEqual(['root', 'a', 'b', 'c']);
  });

  it('shows how deep each agent sits', () => {
    expect(presentSubagentTree(nodes).rows.map((r) => r.depth)).toEqual([0, 1, 2, 1]);
  });

  it('reports the deepest nesting reached', () => {
    expect(presentSubagentTree(nodes).deepest).toBe(2);
  });

  it('counts the agents involved', () => {
    expect(presentSubagentTree(nodes).count).toBe(4);
  });

  it('totals what the whole tree cost', () => {
    expect(presentSubagentTree(nodes).totalCost).toBeCloseTo(1.85, 2);
  });

  it('shows each agent’s own cost', () => {
    const row = presentSubagentTree(nodes).rows.find((r) => r.id === 'a');
    expect(row?.cost).toBeCloseTo(1.0, 2);
  });

  it('marks the agent that failed', () => {
    const row = presentSubagentTree(nodes).rows.find((r) => r.id === 'c');
    expect(row?.state).toBe('failed');
  });

  it('says plainly when something in the tree failed', () => {
    expect(presentSubagentTree(nodes).warning).toBe('1 agent failed');
  });

  it('has no warning when everything is fine', () => {
    const clean = nodes.map((n) => ({ ...n, state: 'done' as const }));
    expect(presentSubagentTree(clean).warning).toBe('');
  });

  it('counts how many are still running', () => {
    expect(presentSubagentTree(nodes).running).toBe(2);
  });

  it('keeps an orphaned agent visible at the top level', () => {
    const orphaned = [...nodes, { id: 'z', name: 'stray', parentId: 'gone', state: 'done' as const, costs: 0 }];
    const rows = presentSubagentTree(orphaned).rows;
    expect(rows.find((r) => r.id === 'z')?.depth).toBe(0);
  });

  it('says which agent is the most expensive', () => {
    expect(presentSubagentTree(nodes).costliest).toBe('researcher');
  });

  it('handles a single agent with no children', () => {
    const alone = [nodes[0]];
    expect(presentSubagentTree(alone).deepest).toBe(0);
  });

  it('handles an empty tree', () => {
    const empty = presentSubagentTree([]);
    expect(empty.rows).toEqual([]);
    expect(empty.costliest).toBe('');
  });
});
