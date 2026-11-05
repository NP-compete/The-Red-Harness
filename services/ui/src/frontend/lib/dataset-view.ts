export interface DatasetState {
  count: number;
  workingCount: number;
  holdoutCount: number;
  excluded: Record<string, string[]>;
  tooSmall: boolean;
}

export interface Exclusion {
  reason: string;
  count: number;
}

export interface PresentedDataset {
  headline: string;
  split: string;
  exclusions: Exclusion[];
  excludedCount: number;
  warning: string;
  usable: boolean;
  action: 'collect-more' | 'none';
}

const REASONS: [string, string][] = [
  ['no-consent', 'Nobody agreed to share these'],
  ['personal-data', 'These contain personal data'],
  ['unlabelled', 'Nobody has labelled these'],
  ['duplicate', 'These are already in the set'],
];

export function presentDataset(dataset: DatasetState): PresentedDataset {
  const exclusions = REASONS.filter(([key]) => (dataset.excluded[key] ?? []).length > 0).map(
    ([key, reason]) => ({ reason, count: dataset.excluded[key].length }),
  );

  return {
    headline: `${dataset.count} case${dataset.count === 1 ? '' : 's'}`,
    split: `${dataset.workingCount} for tuning, ${
      dataset.holdoutCount === 0 ? 'none held back' : `${dataset.holdoutCount} held back`
    }`,
    exclusions,
    excludedCount: exclusions.reduce((sum, item) => sum + item.count, 0),
    warning: warning(dataset),
    usable: !dataset.tooSmall && dataset.holdoutCount > 0,
    action: dataset.tooSmall ? 'collect-more' : 'none',
  };
}

function warning(dataset: DatasetState): string {
  // Size first: a holdout from too few cases is still too few cases.
  if (dataset.tooSmall) return 'Too few cases to tell a real change from noise';
  if (dataset.holdoutCount === 0) {
    return 'With nothing held back, improvements cannot be checked honestly';
  }
  return '';
}
