export interface PrivacySettings {
  region: string;
  retentionDays: number;
  usedForTraining: boolean;
  maskingEnabled: boolean;
  adminCanReadContent: boolean;
}

export interface PrivacyRow {
  title: string;
  detail: string;
  good: boolean;
}

export interface PresentedPrivacy {
  rows: PrivacyRow[];
  actions: Array<'download' | 'delete'>;
  concerns: number;
}

export function presentPrivacy(settings: PrivacySettings): PresentedPrivacy {
  const rows: PrivacyRow[] = [
    {
      title: 'Where it is kept',
      detail: `Processed and stored in ${settings.region}.`,
      good: true,
    },
    {
      title: 'How long it is kept',
      detail: `Kept for ${describeRetention(settings.retentionDays)}, then deleted.`,
      good: true,
    },
    {
      title: 'Model training',
      detail: settings.usedForTraining
        ? 'Your conversations may be used to train a model.'
        : 'Your conversations are not used to train any model.',
      good: !settings.usedForTraining,
    },
    {
      title: 'Personal details',
      detail: settings.maskingEnabled
        ? 'Names, numbers and addresses are masked before the model sees them.'
        : 'Personal details reach the model as written.',
      good: settings.maskingEnabled,
    },
    {
      title: 'Administrators',
      detail: settings.adminCanReadContent
        ? 'Administrators can read what you said.'
        : 'Administrators can see that you used the agent, not what you said.',
      good: !settings.adminCanReadContent,
    },
  ];

  return {
    rows,
    // Always available: being able to leave with your data is not a
    // setting somebody else gets to switch off.
    actions: ['download', 'delete'],
    concerns: rows.filter((row) => !row.good).length,
  };
}

function describeRetention(days: number): string {
  if (days < 60) return `${days} days`;
  return `${Math.round(days / 30.4)} months`;
}
