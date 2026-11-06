/**
 * A person's own documents, and how much room they have left.
 *
 * Only ever theirs. The curated corpus is configuration and is
 * not shown here — listing it on a page with a delete button
 * invites somebody to try.
 */

export interface DocumentRow {
  id: string;
  title: string;
  bytes: number;
}

export interface TeamRow extends DocumentRow {
  team: string;
}

export interface LibraryReport {
  documents: DocumentRow[];
  /** What this person's teams share. Read-only: it comes from
      the configuration tree and returns on the next sync. */
  team?: TeamRow[];
  used_bytes: number;
  limit_bytes: number;
}

export interface LibraryDescription {
  documents: Array<{ id: string; title: string; size: string }>;
  shared: Array<{ id: string; title: string; size: string; team: string }>;
  usedLabel: string;
  limitLabel: string;
  fraction: number;
  nearlyFull: boolean;
}

/** Near enough that the next upload is worth warning about. */
const NEARLY = 0.9;

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function describeLibrary(
  report: LibraryReport | null,
): LibraryDescription | null {
  // "No documents" and "no such page" are different things, and
  // the first invites somebody to add one.
  if (!report || !Array.isArray(report.documents)) return null;

  // A limit of zero is a deployment that keeps a corpus and no
  // personal uploads: full, not NaN.
  const fraction =
    report.limit_bytes > 0
      ? Math.min(1, report.used_bytes / report.limit_bytes)
      : 1;

  return {
    documents: report.documents.map((row) => ({
      id: row.id,
      title: row.title,
      size: formatBytes(row.bytes),
    })),
    shared: (report.team ?? []).map((row) => ({
      id: row.id,
      title: row.title,
      size: formatBytes(row.bytes),
      team: row.team,
    })),
    usedLabel: formatBytes(report.used_bytes),
    limitLabel: formatBytes(report.limit_bytes),
    fraction,
    nearlyFull: fraction >= NEARLY,
  };
}
