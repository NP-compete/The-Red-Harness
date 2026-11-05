import { presentTitle, type TitleSource } from '../lib/title-suggestion-view';
import { cn } from '../lib/utils';

// What the app calls a conversation before anything has named it.
const UNNAMED = new Set(['chat', 'new chat', 'untitled chat', '']);

interface ChatRowTitleProps {
  title: string;
  source?: TitleSource;
}

export function ChatRowTitle({ title, source }: ChatRowTitleProps) {
  const unnamed = UNNAMED.has(title.trim().toLowerCase());
  const presented = presentTitle({
    text: title,
    source: source ?? (unnamed ? 'placeholder' : 'existing'),
    pinned: false,
  });

  return (
    <span
      className={cn('block truncate', presented.placeholder && 'italic text-foreground/60')}
      title={presented.origin || undefined}
    >
      {presented.text}
    </span>
  );
}
