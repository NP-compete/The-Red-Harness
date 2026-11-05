/**
 * How big a file the agent wrote is, in one place.
 *
 * The same figure appears in Settings and beside a reference in the
 * composer. It was written twice, so the two could drift and show
 * different sizes for the same file.
 */
/** A size described rather than worded; the caller supplies the words. */
export type FileSize =
  | { key: 'when.empty' }
  | { key: 'when.kilobytes'; size: string }
  | { key: 'when.bytes'; count: number };

export function fileSize(bytes: number): FileSize {
  if (!Number.isFinite(bytes) || bytes <= 0) return { key: 'when.empty' };
  if (bytes >= 1000) return { key: 'when.kilobytes', size: (bytes / 1000).toFixed(1) };
  return { key: 'when.bytes', count: bytes };
}
