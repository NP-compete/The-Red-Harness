export interface PageItem {
  id: string;
  at: string;
}

export interface PageRequest {
  loaded: number;
  pinnedTop?: string;
}

export interface PresentedPage<T extends PageItem> {
  visible: T[];
  hasMore: boolean;
  remaining: number;
  newAbove: number;
}

export function presentPage<T extends PageItem>(
  items: T[],
  request: PageRequest,
): PresentedPage<T> {
  const ordered = [...items].sort(
    (a, b) => Date.parse(b.at) - Date.parse(a.at) || a.id.localeCompare(b.id),
  );

  // Anchoring on what the reader is already looking at keeps arrivals from
  // pushing the page out from under them.
  const anchor = request.pinnedTop
    ? ordered.findIndex((item) => item.id === request.pinnedTop)
    : -1;
  const offset = anchor > 0 ? anchor : 0;

  const visible = ordered.slice(offset, offset + request.loaded);
  const shown = offset + visible.length;

  return {
    visible,
    hasMore: shown < ordered.length,
    remaining: Math.max(0, ordered.length - shown),
    newAbove: offset,
  };
}
