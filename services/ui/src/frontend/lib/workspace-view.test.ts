import { describe, expect, it } from 'vitest';

import { presentWorkspace } from '@/lib/workspace-view';

const files = [
  { path: 'notes.md', bytes: 1200, writtenAt: '2026-10-27T08:00:00Z', writtenBy: 'agent' as const },
  {
    path: 'out/report.md',
    bytes: 54_000,
    writtenAt: '2026-10-27T08:30:00Z',
    writtenBy: 'agent' as const,
  },
  {
    path: 'out/data.csv',
    bytes: 3_200_000,
    writtenAt: '2026-10-27T08:45:00Z',
    writtenBy: 'person' as const,
  },
];

describe('presentWorkspace', () => {
  it('groups files by folder', () => {
    const shown = presentWorkspace(files);
    expect(shown.folders.map((folder) => folder.name)).toEqual(['/', 'out']);
  });

  it('keeps each folder’s files together', () => {
    const [, out] = presentWorkspace(files).folders;
    expect(out.files.map((file) => file.name)).toEqual(['data.csv', 'report.md']);
  });

  it('shows sizes in units a person reads', () => {
    const [root] = presentWorkspace(files).folders;
    expect(root.files[0].size).toBe('1.2 kB');
  });

  it('shows larger sizes in larger units', () => {
    const [, out] = presentWorkspace(files).folders;
    expect(out.files[0].size).toBe('3.2 MB');
  });

  it('says who wrote each file', () => {
    const [, out] = presentWorkspace(files).folders;
    expect(out.files[0].writtenBy).toBe('you');
  });

  it('names the agent as the writer of its own files', () => {
    const [root] = presentWorkspace(files).folders;
    expect(root.files[0].writtenBy).toBe('the agent');
  });

  it('totals the workspace size', () => {
    expect(presentWorkspace(files).total).toBe('3.3 MB');
  });

  it('counts the files', () => {
    expect(presentWorkspace(files).count).toBe(3);
  });

  it('shows an empty workspace as empty', () => {
    const shown = presentWorkspace([]);
    expect(shown.folders).toEqual([]);
    expect(shown.total).toBe('0 B');
  });

  it('never shows a path that climbs out of the workspace', () => {
    const escaping = [{ ...files[0], path: '../elsewhere/notes.md' }];
    expect(presentWorkspace(escaping).folders).toEqual([]);
  });

  it('counts a refused path as skipped rather than silently dropping it', () => {
    const escaping = [{ ...files[0], path: '../elsewhere/notes.md' }];
    expect(presentWorkspace(escaping).skipped).toBe(1);
  });

  it('never shows an absolute path', () => {
    const absolute = [{ ...files[0], path: '/etc/passwd' }];
    expect(presentWorkspace(absolute).skipped).toBe(1);
  });

  it('skips nothing when every path is ordinary', () => {
    expect(presentWorkspace(files).skipped).toBe(0);
  });
});
