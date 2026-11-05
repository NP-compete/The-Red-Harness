export interface Selection {
  mode: 'none' | 'some' | 'all';
  picked: string[];
  excluded: string[];
}

export interface PageInfo {
  page: string[];
  total: number;
}

export interface ResolvedSelection {
  count: number;
  summary: string;
  beyondThisPage: boolean;
  pageFullySelected: boolean;
  isSelected: (id: string) => boolean;
}

export function resolveSelection(selection: Selection, info: PageInfo): ResolvedSelection {
  const excluded = new Set(selection.excluded);
  const picked = new Set(selection.picked);

  // "All" is a rule, not a list: it covers items this page has never loaded.
  const isSelected =
    selection.mode === 'all'
      ? (id: string) => !excluded.has(id)
      : (id: string) => picked.has(id);

  const count =
    selection.mode === 'all'
      ? Math.max(0, info.total - excluded.size)
      : selection.mode === 'some'
        ? picked.size
        : 0;

  return {
    count,
    summary: summarise(selection, count, info.total),
    beyondThisPage: selection.mode === 'all',
    pageFullySelected: info.page.length > 0 && info.page.every(isSelected),
    isSelected,
  };
}

function summarise(selection: Selection, count: number, total: number): string {
  if (count === 0) return 'Nothing selected';
  if (selection.mode === 'all') {
    return selection.excluded.length === 0
      ? `All ${total} selected`
      : `${count} of ${total} selected`;
  }
  return `${count} selected`;
}
