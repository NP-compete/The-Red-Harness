export interface BriefLine {
  text: string;
  trusted: boolean;
  fenced: boolean;
}

export interface BriefState {
  task: string;
  job: string;
  included: BriefLine[];
  credentials: string[];
  words: number;
  budgetWords: number;
  leftOut: number;
}

export interface PresentedLine {
  text: string;
  quoted: boolean;
}

export interface PresentedBrief {
  headline: string;
  lines: PresentedLine[];
  omitted: string;
  access: string;
  usage: string;
  openByDefault: boolean;
  severity: 'info' | 'medium';
}

export function presentBrief(brief: BriefState): PresentedBrief {
  const shared = brief.credentials.length > 0;

  return {
    headline: `${brief.job}: ${brief.task}`,
    lines: brief.included.map((line) => ({
      text: line.text,
      // Quoted material is shown as something read, not something followed.
      quoted: line.fenced,
    })),
    omitted:
      brief.leftOut > 0
        ? `${brief.leftOut} other thing${brief.leftOut === 1 ? ' was' : 's were'} not passed on`
        : '',
    access: shared ? `Shared: ${brief.credentials.join(', ')}` : 'No credentials were shared',
    usage: `${brief.words} of ${brief.budgetWords} words`,
    // Lending a credential is the one thing here worth opening unprompted.
    openByDefault: shared,
    severity: shared ? 'medium' : 'info',
  };
}
