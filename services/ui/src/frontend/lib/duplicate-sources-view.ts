export interface KeptPassage {
  source: string;
  text: string;
  score: number;
  authority: string;
  alsoIn: string[];
  corroborated: boolean;
}

export interface SourceRow {
  source: string;
  text: string;
  agreement: string;
  confidence: 'corroborated' | 'single source';
  warning: string;
}

export interface PresentedSourceList {
  rows: SourceRow[];
  note: string;
  emptyMessage: string;
}

const INFORMAL = 'note';

export function presentSourceList(kept: KeptPassage[], collapsed: number): PresentedSourceList {
  return {
    rows: kept.map((passage) => ({
      source: passage.source,
      text: passage.text,
      agreement: passage.alsoIn.length > 0 ? `also in ${list(passage.alsoIn)}` : '',
      confidence: passage.corroborated ? 'corroborated' : 'single source',
      // One informal source is the combination worth flagging; a lone policy
      // is thin but authoritative, and saying so of everything says nothing.
      warning:
        !passage.corroborated && passage.authority === INFORMAL
          ? 'This rests on one informal source'
          : '',
    })),
    note:
      collapsed > 0
        ? `${collapsed} repeated passage${collapsed === 1 ? ' was' : 's were'} folded in`
        : '',
    emptyMessage: kept.length === 0 ? 'No sources were used' : '',
  };
}

function list(names: string[]): string {
  if (names.length <= 1) return names[0] ?? '';
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
}
