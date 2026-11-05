export type AnnotationReason = 'flagged' | 'disagreement' | 'low_confidence' | 'failed';

export interface AnnotationEntry {
  item: string;
  reason: AnnotationReason;
}

export interface AnnotationRow {
  item: string;
  why: string;
}

export interface PresentedAnnotationQueue {
  headline: string;
  rows: AnnotationRow[];
  needsAttention: boolean;
}

const WHY: Record<AnnotationReason, string> = {
  flagged: 'Someone asked for another look',
  disagreement: 'The graders disagreed',
  low_confidence: 'The grade was not a confident one',
  failed: 'This item did not pass',
};

export function presentAnnotationQueue(entries: AnnotationEntry[]): PresentedAnnotationQueue {
  const count = entries.length;

  return {
    headline:
      count === 0
        ? 'Nothing needs review'
        : `${count} item${count === 1 ? ' needs' : 's need'} review`,
    rows: entries.map((entry) => ({ item: entry.item, why: WHY[entry.reason] })),
    needsAttention: count > 0,
  };
}
