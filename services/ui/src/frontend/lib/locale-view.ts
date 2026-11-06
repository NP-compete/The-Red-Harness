export type LanguageSource = 'setting' | 'message' | 'workspace';

export interface LocaleState {
  language: string;
  zone: string;
  units: string;
  languageFrom: LanguageSource;
  switched: boolean;
  workspaceLanguage: string;
}

export interface PresentedLocale {
  note: string;
  detail: string;
  action: string;
  dismissible: boolean;
}

export function presentLocale(locale: LocaleState): PresentedLocale | null {
  // Nothing changed, so there is nothing to explain.
  if (!locale.switched) {
    return null;
  }

  const chosen = locale.languageFrom === 'setting';

  return {
    note: `Answering in ${locale.language}, ${chosen ? 'from your settings' : 'matching your message'}`,
    detail: `Times in ${locale.zone} · ${locale.units} units`,
    // Only offer a way back from a choice the person did not make.
    action: chosen ? '' : `Answer in ${locale.workspaceLanguage} instead`,
    dismissible: true,
  };
}
