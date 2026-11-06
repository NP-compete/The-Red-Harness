export interface MemoryRow {
  key: string;
  text: string;
  owner: string;
  ownerIsYou: boolean;
  team: string;
  sharedWithTeam: boolean;
  sensitive: boolean;
  usableHere: boolean;
}

export interface Where {
  sharedThread: boolean;
}

export interface PresentedMemory {
  key: string;
  text: string;
  scope: string;
  author: string;
  inUse: boolean;
  hidden: boolean;
  note: string;
}

export function presentScope(rows: MemoryRow[], where: Where): PresentedMemory[] {
  const presented = rows.map((row) => ({
    key: row.key,
    text: row.text,
    scope: row.sharedWithTeam && row.team ? row.team : 'Only you',
    author: row.ownerIsYou ? '' : row.owner,
    inUse: row.usableHere,
    // Sensitive material stays folded away until someone asks for it.
    hidden: row.sensitive,
    note: row.usableHere
      ? ''
      : where.sharedThread
        ? 'Not used here — others can read this thread'
        : 'Not used here',
  }));

  return presented.sort((a, b) => Number(b.inUse) - Number(a.inUse));
}
