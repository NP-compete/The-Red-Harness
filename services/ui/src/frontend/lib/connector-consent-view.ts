export interface ConnectorPreview {
  source: string;
  reads: string[];
  documents: number;
  actsAs: string;
  warnings: string[];
  readOnly: boolean;
  needsCarefulConsent: boolean;
}

export interface PresentedConnectorConsent {
  headline: string;
  scope: string;
  size: string;
  access: string;
  warnings: string[];
  actions: string[];
  severity: 'info' | 'medium' | 'high';
}

export function presentConnectorConsent(preview: ConnectorPreview): PresentedConnectorConsent {
  let severity: PresentedConnectorConsent['severity'] = 'info';
  if (preview.needsCarefulConsent) {
    severity = preview.readOnly ? 'medium' : 'high';
  }

  return {
    headline: `Connect ${preview.source}`,
    scope: `Reads: ${preview.reads.join(', ')}`,
    size: `About ${preview.documents} documents`,
    access: preview.readOnly
      ? `Read only, as ${preview.actsAs}`
      : `Can read and change things, as ${preview.actsAs}`,
    warnings: preview.warnings,
    // A broad grant is agreed to in words, not waved through on a default button.
    actions: preview.needsCarefulConsent
      ? ['I understand — connect', 'Choose folders instead', 'Cancel']
      : ['Connect', 'Cancel'],
    severity,
  };
}
