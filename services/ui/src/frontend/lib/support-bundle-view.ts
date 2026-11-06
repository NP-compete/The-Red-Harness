export interface BundleState {
  sections: string[];
  redactions: number;
  sizeBytes: number;
  createdAt: string;
  expiresAt: string;
  downloadUrl: string;
}

export interface PresentedBundle {
  contents: string[];
  redactionNote: string;
  size: string;
  expires: string;
  advice: string;
  downloadUrl: string | null;
  action: 'download' | 'rebuild';
}

const DAY = 86_400_000;

export function presentBundle(bundle: BundleState, now: Date): PresentedBundle {
  const remaining = Date.parse(bundle.expiresAt) - now.getTime();
  const live = remaining > 0;

  return {
    contents: bundle.sections,
    redactionNote:
      bundle.redactions === 0
        ? 'No secrets were found to remove'
        : `${bundle.redactions} secret${bundle.redactions === 1 ? ' was' : 's were'} removed`,
    size: size(bundle.sizeBytes),
    expires: live ? `deleted in ${Math.round(remaining / DAY)} days` : 'deleted',
    // Removal is best effort; the reader still has to look.
    advice: 'Review the contents before sharing this outside your organisation',
    downloadUrl: live ? bundle.downloadUrl : null,
    action: live ? 'download' : 'rebuild',
  };
}

function size(bytes: number): string {
  if (bytes >= 1e6) return `${trim((bytes / 1e6).toFixed(1))} MB`;
  if (bytes >= 1e3) return `${trim((bytes / 1e3).toFixed(1))} kB`;
  return `${bytes} B`;
}

function trim(value: string): string {
  return value.endsWith('.0') ? value.slice(0, -2) : value;
}
