export interface PreviewChunk {
  index: number;
  text: string;
}

export interface SourcePreview {
  document: string;
  chunks: PreviewChunk[];
  matchedIndex: number;
  trimmed: boolean;
  words: number;
  updatedAt: string | null;
}

export interface PreviewPart {
  text: string;
  matched: boolean;
}

export interface PresentedSourcePreview {
  title: string;
  parts: PreviewPart[];
  extent: string;
  note: string;
  updated: string;
  action: 'open-document';
}

const DAY = 86_400_000;

export function presentSourcePreview(
  preview: SourcePreview,
  now: Date,
): PresentedSourcePreview {
  const count = preview.chunks.length;

  return {
    title: preview.document,
    parts: preview.chunks.map((chunk) => ({
      text: chunk.text,
      matched: chunk.index === preview.matchedIndex,
    })),
    extent:
      count === 0
        ? 'nothing to show'
        : `${preview.words} words from ${count} passage${count === 1 ? '' : 's'}`,
    // Said plainly, so missing context never reads as absent context.
    note: preview.trimmed ? 'Surrounding text was left out for space' : '',
    updated: updated(preview.updatedAt, now),
    action: 'open-document',
  };
}

function updated(at: string | null, now: Date): string {
  if (at === null) return 'update date unknown';
  const days = Math.round((now.getTime() - Date.parse(at)) / DAY);
  if (days < 1) return 'updated today';
  return `updated ${days} day${days === 1 ? '' : 's'} ago`;
}
