export type AgentState = 'running' | 'done' | 'failed';

export interface AgentNode {
  id: string;
  name: string;
  parentId: string | null;
  state: AgentState;
  costs: number;
}

export interface AgentRow {
  id: string;
  name: string;
  depth: number;
  state: AgentState;
  cost: number;
}

export interface PresentedTree {
  rows: AgentRow[];
  count: number;
  deepest: number;
  running: number;
  totalCost: number;
  costliest: string;
  warning: string;
}

export function presentSubagentTree(nodes: AgentNode[]): PresentedTree {
  const known = new Set(nodes.map((node) => node.id));
  const children = new Map<string | null, AgentNode[]>();

  for (const node of nodes) {
    // An agent whose parent is missing is still shown, at the top level,
    // rather than disappearing with the record of its parent.
    const parent = node.parentId && known.has(node.parentId) ? node.parentId : null;
    children.set(parent, [...(children.get(parent) ?? []), node]);
  }

  const rows: AgentRow[] = [];
  const walk = (parent: string | null, depth: number): void => {
    for (const node of children.get(parent) ?? []) {
      rows.push({ id: node.id, name: node.name, depth, state: node.state, cost: node.costs });
      walk(node.id, depth + 1);
    }
  };
  walk(null, 0);

  const failed = nodes.filter((node) => node.state === 'failed').length;
  const costliest = [...nodes].sort((a, b) => b.costs - a.costs)[0];

  return {
    rows,
    count: nodes.length,
    deepest: rows.reduce((deepest, row) => Math.max(deepest, row.depth), 0),
    running: nodes.filter((node) => node.state === 'running').length,
    totalCost: nodes.reduce((sum, node) => sum + node.costs, 0),
    costliest: costliest ? costliest.name : '',
    warning: failed > 0 ? `${failed} agent${failed === 1 ? '' : 's'} failed` : '',
  };
}
