export interface WorkspaceFile {
  path: string;
  bytes: number;
  writtenAt: string;
  writtenBy: 'agent' | 'person';
}

export interface PresentedFile {
  name: string;
  size: string;
  writtenAt: string;
  writtenBy: string;
}

export interface PresentedFolder {
  name: string;
  files: PresentedFile[];
}

export interface PresentedWorkspace {
  folders: PresentedFolder[];
  total: string;
  count: number;
  skipped: number;
}

const ROOT = '/';

export function presentWorkspace(files: WorkspaceFile[]): PresentedWorkspace {
  const safe = files.filter((file) => isInside(file.path));
  const byFolder = new Map<string, PresentedFile[]>();

  for (const file of safe) {
    const cut = file.path.lastIndexOf('/');
    const folder = cut === -1 ? ROOT : file.path.slice(0, cut);
    const name = cut === -1 ? file.path : file.path.slice(cut + 1);
    byFolder.set(folder, [
      ...(byFolder.get(folder) ?? []),
      {
        name,
        size: size(file.bytes),
        writtenAt: file.writtenAt,
        writtenBy: file.writtenBy === 'person' ? 'you' : 'the agent',
      },
    ]);
  }

  const folders = [...byFolder.entries()]
    .map(([name, contents]) => ({
      name,
      files: [...contents].sort((a, b) => a.name.localeCompare(b.name)),
    }))
    .sort((a, b) => (a.name === ROOT ? -1 : b.name === ROOT ? 1 : a.name.localeCompare(b.name)));

  return {
    folders,
    total: size(safe.reduce((sum, file) => sum + file.bytes, 0)),
    count: safe.length,
    skipped: files.length - safe.length,
  };
}

function isInside(path: string): boolean {
  if (path.startsWith('/')) return false;
  return !path.split('/').includes('..');
}

function size(bytes: number): string {
  const units: [number, string][] = [
    [1e9, 'GB'],
    [1e6, 'MB'],
    [1e3, 'kB'],
  ];
  for (const [scale, unit] of units) {
    if (bytes >= scale) return `${trim((bytes / scale).toFixed(1))} ${unit}`;
  }
  return `${bytes} B`;
}

function trim(value: string): string {
  return value.endsWith('.0') ? value.slice(0, -2) : value;
}
