export interface PruningState {
  keptCount: number;
  capacity: number;
  dropped: string[];
  overCapacity: boolean;
  pinnedCount: number;
}

export interface PresentedPruning {
  headline: string;
  usage: string;
  forgotten: string[];
  pinnedNote: string;
  warning: string;
  severity: 'info' | 'medium';
  dismissible: true;
  action: 'restore';
}

export function presentPruning(state: PruningState): PresentedPruning | null {
  // Silent forgetting is the thing people find unnerving; say it or say nothing.
  if (state.dropped.length === 0) return null;

  const count = state.dropped.length;

  return {
    headline: `Forgot ${count} thing${count === 1 ? '' : 's'} to make room`,
    usage: `${state.keptCount} of ${state.capacity} remembered`,
    forgotten: state.dropped,
    pinnedNote:
      state.pinnedCount > 0
        ? `${state.pinnedCount} are pinned and will never be forgotten`
        : '',
    warning: state.overCapacity
      ? 'More is pinned than there is room for, so nothing else can be remembered'
      : '',
    severity: state.overCapacity ? 'medium' : 'info',
    dismissible: true,
    action: 'restore',
  };
}
