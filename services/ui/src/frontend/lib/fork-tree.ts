export interface BranchSummary {
  name: string;
  messages: number;
  from?: string;
  at?: string;
}

export interface ForkRow {
  name: string;
  depth: number;
  messages: number;
  takenAt?: string;
  current: boolean;
}

export interface PresentedForkTree {
  rows: ForkRow[];
  forkCount: number;
}

export function presentForkTree(
  branches: BranchSummary[],
  { current }: { current: string },
): PresentedForkTree {
  const byName = new Map(branches.map((branch) => [branch.name, branch]));

  const rows = branches.map<ForkRow>((branch) => ({
    name: branch.name,
    depth: depthOf(branch, byName),
    messages: branch.messages,
    takenAt: branch.at,
    current: branch.name === current,
  }));

  return { rows, forkCount: branches.filter((branch) => branch.from !== undefined).length };
}

function depthOf(branch: BranchSummary, byName: Map<string, BranchSummary>): number {
  let depth = 0;
  let parent = branch.from;
  const seen = new Set<string>([branch.name]);

  // A missing or circular parent still gets a row: losing a branch from
  // the list is worse than drawing it at the wrong indent.
  while (parent !== undefined && byName.has(parent) && !seen.has(parent)) {
    seen.add(parent);
    depth += 1;
    parent = byName.get(parent)?.from;
  }
  return depth;
}
