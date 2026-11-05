import type { SecretFinding, SecretReport } from './secret-warning-view';

/**
 * Look for credentials in a message before it is sent.
 *
 * Done here rather than by the agent: asking the server whether a
 * message contains a secret means sending it the secret, which is the
 * thing being prevented.
 */

const MIN_PASSWORD = 6;
const MIN_KEY = 12;
const PLACEHOLDERS = new Set(['', 'redacted', 'none', 'null', 'changeme', 'example']);

const VALUE = String.raw`(?:"([^"]*)"|'([^']*)'|(\S+))`;

const PATTERNS: { kind: string; pattern: RegExp; minimum: number }[] = [
  { kind: 'private-key', pattern: /-----BEGIN [A-Z ]*PRIVATE KEY-----/, minimum: 0 },
  { kind: 'bearer-token', pattern: /\bbearer\s+(\S+)/i, minimum: MIN_KEY },
  {
    kind: 'connection-string',
    pattern: /\b[a-z][a-z0-9+.-]*:\/\/[^\s:/@]+:([^\s:/@]+)@/,
    minimum: MIN_PASSWORD,
  },
  {
    kind: 'password',
    pattern: new RegExp(String.raw`\b(?:password|passwd|pwd|secret)\s*[=:]\s*${VALUE}`, 'i'),
    minimum: MIN_PASSWORD,
  },
  {
    kind: 'api-key',
    pattern: new RegExp(
      String.raw`\b[a-z_]*(?:api[_-]?key|access[_-]?token|token)\s*[=:]\s*${VALUE}`,
      'i',
    ),
    minimum: MIN_KEY,
  },
];

export interface OutgoingScan extends SecretReport {
  /** Guards the rule that an excerpt never quotes the secret itself. */
  excerptsContainSecret: boolean;
}

export function scanOutgoing(text: string): OutgoingScan {
  const findings: SecretFinding[] = [];
  const secrets: string[] = [];

  text.split('\n').forEach((line, index) => {
    for (const { kind, pattern, minimum } of PATTERNS) {
      const match = pattern.exec(line);
      if (!match) continue;

      const value = (match[1] ?? match[2] ?? match[3] ?? '').trim();
      if (minimum > 0) {
        if (value.length < minimum) continue;
        if (PLACEHOLDERS.has(value.toLowerCase())) continue;
      }

      if (value) secrets.push(value);
      findings.push({
        kind,
        line: index + 1,
        // The words around it, never the credential: an excerpt that
        // quotes the secret puts it on screen to prove it is on screen.
        excerpt: line.slice(0, match.index).trim() || line.slice(0, 20).trim(),
      });
      break;
    }
  });

  return {
    findings,
    // Never blocked: a composer that refuses to send loses the message.
    safeToSend: true,
    summary: findings.length === 0 ? '' : `${findings.length} possible credential(s)`,
    excerptsContainSecret: findings.some((finding) =>
      secrets.some((secret) => secret.length > 0 && finding.excerpt.includes(secret)),
    ),
  };
}
