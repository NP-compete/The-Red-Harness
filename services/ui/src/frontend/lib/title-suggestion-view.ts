export type TitleSource = 'first-message' | 'attachment' | 'existing' | 'placeholder';

export interface SuggestedTitle {
  text: string;
  source: TitleSource;
  pinned: boolean;
}

export interface PresentedTitle {
  text: string;
  origin: string;
  placeholder: boolean;
  editable: true;
  keepsOnNewMessages: boolean;
  action: 'rename' | 'none';
}

const ORIGINS: Record<TitleSource, string> = {
  'first-message': 'named from your first message',
  attachment: 'named after the attached file',
  placeholder: 'not named yet',
  existing: '',
};

export function presentTitle(title: SuggestedTitle): PresentedTitle {
  const placeholder = title.source === 'placeholder';

  return {
    // A blank name in a list is a row nobody can identify.
    text: title.text.trim() || 'Untitled',
    origin: ORIGINS[title.source],
    placeholder,
    editable: true,
    // Only a name someone chose survives the next automatic attempt.
    keepsOnNewMessages: title.pinned,
    action: title.pinned ? 'none' : placeholder ? 'rename' : 'none',
  };
}
