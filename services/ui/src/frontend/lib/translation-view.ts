export type Handling = 'as_is' | 'translate' | 'untranslated';

export interface ReadingStep {
  chunk: string;
  language: string;
  handling: Handling;
  languageUncertain: boolean;
}

export interface PresentedTranslation {
  note: string;
  warning: string;
  chunks: string[];
  severity: 'info' | 'low';
}

function languages(steps: ReadingStep[]): string {
  return [...new Set(steps.map((step) => step.language))].join(', ');
}

export function presentTranslation(plan: ReadingStep[]): PresentedTranslation | null {
  const translated = plan.filter((step) => step.handling === 'translate');
  const untranslated = plan.filter((step) => step.handling === 'untranslated');

  // Nothing was read in another language, so there is nothing to disclose.
  if (translated.length === 0 && untranslated.length === 0) {
    return null;
  }

  const count = translated.length;

  return {
    note:
      count === 0
        ? ''
        : `${count} source${count === 1 ? ' was' : 's were'} translated from ${languages(translated)}`,
    warning:
      untranslated.length === 0
        ? ''
        : `${untranslated.length} source${untranslated.length === 1 ? ' is' : 's are'} shown in ${languages(untranslated)}, untranslated`,
    chunks: translated.map((step) => step.chunk),
    severity: untranslated.length > 0 ? 'low' : 'info',
  };
}
