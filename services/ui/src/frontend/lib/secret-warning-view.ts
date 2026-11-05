export interface SecretFinding {
  kind: string;
  line: number;
  excerpt: string;
}

export interface SecretReport {
  findings: SecretFinding[];
  safeToSend: boolean;
  summary: string;
}

export interface PresentedSecretWarning {
  headline: string;
  locations: string[];
  excerpts: string[];
  blocked: boolean;
  override: string;
  overrideNote: string;
}

const NAMES: Record<string, string> = {
  'private-key': 'a private key',
  'bearer-token': 'an access token',
  'connection-string': 'a database password',
  password: 'a password',
  'api-key': 'an API key',
};

export function presentSecretWarning(report: SecretReport): PresentedSecretWarning | null {
  if (report.findings.length === 0) return null;

  return {
    headline: `This message looks like it contains ${describe(report.findings)}`,
    locations: report.findings.map((finding) => `line ${finding.line}`),
    excerpts: report.findings.map((finding) => finding.excerpt),
    blocked: !report.safeToSend,
    override: 'send anyway',
    overrideNote: 'Sending anyway is recorded against this run.',
  };
}

function describe(findings: SecretFinding[]): string {
  if (findings.length > 1) return `${findings.length} credentials`;
  return NAMES[findings[0].kind] ?? 'a credential';
}
