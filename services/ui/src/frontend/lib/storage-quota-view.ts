export interface StorageState {
  state: 'fine' | 'nearly-full' | 'full';
  shareUsed: number;
  remainingBytes: number;
  couldFreeBytes: number;
  mayAccept: boolean;
  reason: string;
}

export interface PresentedStorage {
  headline: string;
  detail: string;
  stillPossible: string;
  couldFree: string;
  bar: number;
  canUpload: boolean;
  severity: 'medium' | 'high';
  action: 'clear-old' | 'request-more';
}

export function presentStorage(storage: StorageState): PresentedStorage | null {
  if (storage.state === 'fine' && storage.mayAccept) return null;

  const full = storage.state === 'full';

  return {
    headline: full ? 'Storage is full' : `${size(storage.remainingBytes)} of storage left`,
    detail: storage.reason,
    // Said plainly, because a full store looks like a broken one.
    stillPossible: full ? 'You can still read and delete what is here' : '',
    couldFree: storage.couldFreeBytes > 0 ? `${size(storage.couldFreeBytes)} could be cleared` : '',
    bar: storage.shareUsed,
    canUpload: storage.mayAccept,
    severity: full ? 'high' : 'medium',
    // Clearing is in the team's own hands; asking for more is not.
    action: storage.couldFreeBytes > 0 ? 'clear-old' : 'request-more',
  };
}

function size(bytes: number): string {
  if (bytes >= 1e6) return `${trim((bytes / 1e6).toFixed(1))} MB`;
  if (bytes >= 1e3) return `${trim((bytes / 1e3).toFixed(1))} kB`;
  return `${bytes} B`;
}

function trim(value: string): string {
  return value.endsWith('.0') ? value.slice(0, -2) : value;
}
