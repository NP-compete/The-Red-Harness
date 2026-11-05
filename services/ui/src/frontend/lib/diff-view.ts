export interface ProposedChange {
  path: string;
  added: number;
  removed: number;
  kind: 'edit' | 'create' | 'delete';
}

export interface PresentedChange {
  path: string;
  kind: ProposedChange['kind'];
  description: string;
  attention: boolean;
}

export interface PresentedChangeSet {
  summary: string;
  files: PresentedChange[];
  refused: string[];
  canApprove: boolean;
  allOrNothing: true;
}

const LARGE_EDIT = 500;
const ORDER: Record<ProposedChange['kind'], number> = { delete: 0, edit: 1, create: 2 };

export function presentProposedChanges(changes: ProposedChange[]): PresentedChangeSet {
  const safe = changes.filter((change) => isInside(change.path));
  const refused = changes.filter((change) => !isInside(change.path)).map((change) => change.path);

  const added = safe.reduce((sum, change) => sum + change.added, 0);
  const removed = safe.reduce((sum, change) => sum + change.removed, 0);

  return {
    summary: safe.length
      ? `${safe.length} file${safe.length === 1 ? '' : 's'} changed, ${added} added, ${removed} removed`
      : 'No changes proposed',
    files: [...safe]
      .sort((a, b) => ORDER[a.kind] - ORDER[b.kind] || a.path.localeCompare(b.path))
      .map((change) => ({
        path: change.path,
        kind: change.kind,
        description: describe(change),
        attention: change.kind === 'delete' || change.added + change.removed > LARGE_EDIT,
      })),
    refused,
    canApprove: refused.length === 0 && safe.length > 0,
    // Applying half a change set leaves the tree in a state nobody reviewed.
    allOrNothing: true,
  };
}

function describe(change: ProposedChange): string {
  if (change.kind === 'delete') return 'deleted';
  if (change.kind === 'create') return `new file, ${change.added} lines`;
  return `${change.added} added, ${change.removed} removed`;
}

function isInside(path: string): boolean {
  if (path.startsWith('/')) return false;
  return !path.split('/').includes('..');
}
