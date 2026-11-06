export interface SearchResult {
  id: string;
  title: string;
  when: string;
  sharedByOther: boolean;
}

export interface SearchRow {
  id: string;
  when: string;
  // Split into before, match, after so the view can emphasise the
  // middle without building markup from a user-supplied string.
  highlight: string[];
  note: string;
}

export interface PresentedSearch {
  rows: SearchRow[];
  summary: string;
}

export function presentSearch(query: string, results: SearchResult[]): PresentedSearch {
  const needle = query.trim();
  if (!needle) {
    return { rows: [], summary: 'Type to search your conversations' };
  }

  const rows = results.map<SearchRow>((result) => ({
    id: result.id,
    when: result.when,
    highlight: split(result.title, needle),
    note: result.sharedByOther ? 'Shared with you' : '',
  }));

  return { rows, summary: summarise(rows.length, needle) };
}

function split(title: string, needle: string): string[] {
  const at = title.toLowerCase().indexOf(needle.toLowerCase());
  if (at === -1) return [title];
  return [title.slice(0, at), title.slice(at, at + needle.length), title.slice(at + needle.length)];
}

function summarise(count: number, needle: string): string {
  if (count === 0) return `Nothing found for “${needle}”`;
  return count === 1 ? '1 conversation' : `${count} conversations`;
}
