export interface ExportRequest {
  scope: 'thread' | 'project' | 'everything';
  format: 'json' | 'markdown' | 'csv';
  includeAttachments: boolean;
  containsSensitiveData: boolean;
  itemCount: number;
  state: 'ready' | 'running' | 'done';
  progress: number;
  downloadUrl: string | null;
  expiresAt: string | null;
}

export interface PresentedExport {
  summary: string;
  includes: string;
  warning: string;
  status: string;
  downloadUrl: string | null;
  canStart: boolean;
}

const FORMATS: Record<ExportRequest['format'], string> = {
  json: 'JSON',
  markdown: 'Markdown',
  csv: 'CSV',
};

export function presentExport(request: ExportRequest, now: Date): PresentedExport {
  const expired =
    request.expiresAt !== null && Date.parse(request.expiresAt) <= now.getTime();
  const running = request.state === 'running';
  const finished = request.state === 'done' && !expired;

  return {
    summary: `${request.itemCount} conversation${request.itemCount === 1 ? '' : 's'} as ${FORMATS[request.format]}`,
    includes: request.includeAttachments ? 'conversations and attachments' : 'conversations only',
    warning: request.containsSensitiveData
      ? 'This export contains sensitive data that will leave the platform'
      : '',
    status: status(request, { running, finished, expired, now }),
    // An expired link is not offered, so nobody clicks into a dead end.
    downloadUrl: finished ? request.downloadUrl : null,
    canStart: !running,
  };
}

function status(
  request: ExportRequest,
  flags: { running: boolean; finished: boolean; expired: boolean; now: Date },
): string {
  if (flags.running) return `${Math.round(request.progress * 100)}% done`;
  if (flags.expired) return 'The file has expired';
  if (flags.finished && request.expiresAt) {
    const hours = Math.round(
      (Date.parse(request.expiresAt) - flags.now.getTime()) / 3_600_000,
    );
    return `Ready, available for ${hours} hour${hours === 1 ? '' : 's'}`;
  }
  return '';
}
