import { describe, expect, it } from 'vitest';

import { presentProposedChanges } from '@/lib/diff-view';

const changes = [
  { path: 'src/app.ts', added: 12, removed: 3, kind: 'edit' as const },
  { path: 'src/new.ts', added: 40, removed: 0, kind: 'create' as const },
  { path: 'src/old.ts', added: 0, removed: 80, kind: 'delete' as const },
];

describe('presentProposedChanges', () => {
  it('summarises the whole change in one line', () => {
    expect(presentProposedChanges(changes).summary).toBe(
      '3 files changed, 52 added, 83 removed',
    );
  });

  it('uses the singular for a single file', () => {
    expect(presentProposedChanges([changes[0]]).summary).toBe(
      '1 file changed, 12 added, 3 removed',
    );
  });

  it('says plainly when nothing is proposed', () => {
    expect(presentProposedChanges([]).summary).toBe('No changes proposed');
  });

  it('puts deletions first so they are not missed', () => {
    expect(presentProposedChanges(changes).files.map((file) => file.path)).toEqual([
      'src/old.ts',
      'src/app.ts',
      'src/new.ts',
    ]);
  });

  it('describes each file in words', () => {
    const [deleted, edited, created] = presentProposedChanges(changes).files;
    expect(deleted.description).toBe('deleted');
    expect(edited.description).toBe('12 added, 3 removed');
    expect(created.description).toBe('new file, 40 lines');
  });

  it('marks a deletion as needing a closer look', () => {
    expect(presentProposedChanges(changes).files[0].attention).toBe(true);
  });

  it('does not mark an ordinary edit', () => {
    expect(presentProposedChanges(changes).files[1].attention).toBe(false);
  });

  it('marks an unusually large edit', () => {
    const big = [{ path: 'src/huge.ts', added: 900, removed: 400, kind: 'edit' as const }];
    expect(presentProposedChanges(big).files[0].attention).toBe(true);
  });

  it('says the change cannot be applied in part', () => {
    expect(presentProposedChanges(changes).allOrNothing).toBe(true);
  });

  it('refuses a change that touches a path outside the workspace', () => {
    const escaping = [{ path: '../elsewhere/app.ts', added: 1, removed: 0, kind: 'edit' as const }];
    expect(presentProposedChanges(escaping).files).toEqual([]);
  });

  it('says a refused path was refused rather than hiding it', () => {
    const escaping = [{ path: '../elsewhere/app.ts', added: 1, removed: 0, kind: 'edit' as const }];
    expect(presentProposedChanges(escaping).refused).toEqual(['../elsewhere/app.ts']);
  });

  it('blocks approval when any path was refused', () => {
    const escaping = [{ path: '/etc/passwd', added: 1, removed: 0, kind: 'edit' as const }];
    expect(presentProposedChanges(escaping).canApprove).toBe(false);
  });

  it('allows approval when every path is ordinary', () => {
    expect(presentProposedChanges(changes).canApprove).toBe(true);
  });
});
