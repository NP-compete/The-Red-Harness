import { useCallback, useMemo, useState } from 'react';

import { resolveSelection, type Selection } from '../lib/bulk-select';

const NOTHING: Selection = { mode: 'none', picked: [], excluded: [] };

export interface ThreadSelection {
  count: number;
  summary: string;
  beyondThisPage: boolean;
  pageFullySelected: boolean;
  isSelected: (id: string) => boolean;
  /** The visible rows currently covered by the selection. */
  pickedOnPage: () => string[];
  /** Everything covered, including rows this list has never loaded. */
  targets: (allIds: string[]) => string[];
  toggle: (id: string) => void;
  selectAll: () => void;
  clear: () => void;
}

/**
 * Which conversations are picked.
 *
 * "All" is kept as a rule rather than a list, so it still means
 * everything after more rows load.
 */
export function useThreadSelection(page: string[], total: number): ThreadSelection {
  const [selection, setSelection] = useState<Selection>(NOTHING);

  const resolved = useMemo(
    () => resolveSelection(selection, { page, total }),
    [selection, page, total],
  );

  const toggle = useCallback((id: string) => {
    setSelection((current) => {
      if (current.mode === 'all') {
        const excluded = current.excluded.includes(id)
          ? current.excluded.filter((x) => x !== id)
          : [...current.excluded, id];
        return { ...current, excluded };
      }
      const picked = current.picked.includes(id)
        ? current.picked.filter((x) => x !== id)
        : [...current.picked, id];
      return { mode: picked.length > 0 ? 'some' : 'none', picked, excluded: [] };
    });
  }, []);

  const selectAll = useCallback(
    () => setSelection({ mode: 'all', picked: [], excluded: [] }),
    [],
  );
  const clear = useCallback(() => setSelection(NOTHING), []);

  const pickedOnPage = useCallback(
    () => page.filter((id) => resolved.isSelected(id)),
    [page, resolved],
  );

  // "All" has to be applied against the real list, not the visible one.
  const targets = useCallback(
    (allIds: string[]) => allIds.filter((id) => resolved.isSelected(id)),
    [resolved],
  );

  return {
    count: resolved.count,
    summary: resolved.summary,
    beyondThisPage: resolved.beyondThisPage,
    pageFullySelected: resolved.pageFullySelected,
    isSelected: resolved.isSelected,
    pickedOnPage,
    targets,
    toggle,
    selectAll,
    clear,
  };
}
