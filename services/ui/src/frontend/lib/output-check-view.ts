export interface OutputCheck {
  fits: boolean;
  missing: string[];
  wrongShape: string[];
  tooLong: string[];
  unexpected: string[];
  detail: string;
}

export interface PresentedOutputCheck {
  headline: string;
  detail: string;
  note: string;
  severity: 'low' | 'medium' | 'high';
  action: 'ask-again' | 'shorten';
}

export function presentOutputCheck(check: OutputCheck): PresentedOutputCheck | null {
  // Extra material is worth mentioning but is not a failure on its own.
  if (check.fits) return null;

  const headline = describe(check);

  return {
    headline,
    detail: check.detail,
    note:
      check.unexpected.length > 0
        ? `It also included ${list(check.unexpected)}, which was not asked for`
        : '',
    severity: severity(check),
    // Length is a trim; anything else needs the answer produced again.
    action: onlyLength(check) ? 'shorten' : 'ask-again',
  };
}

function describe(check: OutputCheck): string {
  if (check.missing.length > 0) return `The answer is missing ${list(check.missing)}`;
  if (check.wrongShape.length > 0) {
    return `${list(check.wrongShape)} is not in the form that was asked for`;
  }
  return `${list(check.tooLong)} is longer than asked for`;
}

function severity(check: OutputCheck): 'low' | 'medium' | 'high' {
  if (check.missing.length > 0) return 'high';
  if (check.wrongShape.length > 0) return 'medium';
  return 'low';
}

function onlyLength(check: OutputCheck): boolean {
  return check.missing.length === 0 && check.wrongShape.length === 0;
}

function list(names: string[]): string {
  if (names.length <= 1) return names[0] ?? '';
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
}
