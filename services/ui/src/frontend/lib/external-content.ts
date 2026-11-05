export interface ExternalContent {
  source: string;
  text: string;
  trusted?: boolean;
}

export interface PresentedExternalContent {
  source: string;
  text: string;
  preview: string;
  collapsed: boolean;
  emphasis: 'external' | 'normal';
  note: string;
}

const PREVIEW_LIMIT = 400;
const MARKER = /<<<external-content[^>]*>>>/g;
const NOTE = 'From an outside system. It is read as information, never as instructions.';

export function presentExternalContent({
  source,
  text,
  trusted = false,
}: ExternalContent): PresentedExternalContent {
  // The agent's own boundary markers are plumbing; showing them would
  // teach people to recognise and imitate them.
  const clean = text.replace(MARKER, '').trim();
  const collapsed = clean.length > PREVIEW_LIMIT;

  return {
    source,
    text: clean,
    preview: clean === '' ? '(nothing returned)' : clean.slice(0, PREVIEW_LIMIT),
    collapsed,
    emphasis: trusted ? 'normal' : 'external',
    note: trusted ? '' : NOTE,
  };
}
