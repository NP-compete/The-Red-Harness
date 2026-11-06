export interface MemoryChange {
  key: string;
  label: string;
  resolution: 'added' | 'unchanged' | 'superseded' | 'kept-existing';
  keptValue: string;
  replacedValue: string;
  source: 'stated' | 'inferred';
  worthMentioning: boolean;
}

export interface PresentedMemoryChange {
  headline: string;
  detail: string;
  severity: 'info';
  dismissible: true;
  action: 'correct';
  secondaryAction: 'forget';
}

export function presentMemoryChange(change: MemoryChange): PresentedMemoryChange | null {
  if (!change.worthMentioning) return null;

  const label = change.label || humanise(change.key);

  return {
    headline:
      change.resolution === 'kept-existing'
        ? `Still remembering ${label} as ${change.keptValue}`
        : `${label} is now ${change.keptValue}${
            change.replacedValue ? `, not ${change.replacedValue}` : ''
          }`,
    detail:
      change.source === 'stated'
        ? 'Because you said so'
        : 'This was guessed from how you work, so it did not replace what you told me',
    // Remembering something is not an alarm; it still has to be correctable.
    severity: 'info',
    dismissible: true,
    action: 'correct',
    secondaryAction: 'forget',
  };
}

function humanise(key: string): string {
  const words = key.replace(/[-_]/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}
