export interface Source {
  document: string;
  snippet: string;
  score: number;
}

export interface CitedSource {
  marker: string;
  document: string;
  snippet: string;
}

export interface PresentedSources {
  cited: CitedSource[];
  alsoFound: Source[];
  counts: { cited: number; alsoFound: number };
  warning?: string;
}

const SNIPPET_LIMIT = 200;

export function presentSources({
  used,
  unused,
}: {
  used: Source[];
  unused: Source[];
}): PresentedSources {
  const cited = used.map<CitedSource>((source, index) => ({
    marker: String(index + 1),
    document: source.document,
    snippet: shorten(source.snippet),
  }));

  const alsoFound = unused.filter(
    (source, index, all) =>
      all.findIndex((other) => other.document === source.document) === index,
  );

  return {
    cited,
    alsoFound,
    counts: { cited: cited.length, alsoFound: alsoFound.length },
    warning: warn(cited.length, unused.length),
  };
}

function warn(cited: number, retrieved: number): string | undefined {
  if (cited > 0) return undefined;
  return retrieved === 0
    ? 'No sources were searched for this answer.'
    : 'This answer is not based on any of the sources that were found.';
}

function shorten(snippet: string): string {
  return snippet.length <= SNIPPET_LIMIT ? snippet : `${snippet.slice(0, SNIPPET_LIMIT)}…`;
}
