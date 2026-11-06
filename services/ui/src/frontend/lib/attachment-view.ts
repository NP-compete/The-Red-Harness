export interface Attachment {
  name: string;
  bytes: number;
  scanned: boolean;
  safe: boolean;
  fromAgent: boolean;
}

export type AttachmentKind = 'document' | 'image' | 'spreadsheet' | 'program' | 'file';

export interface PresentedAttachment {
  name: string;
  size: string;
  kind: AttachmentKind;
  status: string;
  origin: string;
  warning: string;
  canPreview: boolean;
  canDownload: boolean;
}

const KINDS: Record<string, AttachmentKind> = {
  pdf: 'document',
  doc: 'document',
  docx: 'document',
  txt: 'document',
  md: 'document',
  png: 'image',
  jpg: 'image',
  jpeg: 'image',
  gif: 'image',
  webp: 'image',
  csv: 'spreadsheet',
  xls: 'spreadsheet',
  xlsx: 'spreadsheet',
  exe: 'program',
  bat: 'program',
  sh: 'program',
  cmd: 'program',
  msi: 'program',
};

const PREVIEWABLE = new Set<AttachmentKind>(['document', 'image', 'spreadsheet']);

export function presentAttachment(file: Attachment): PresentedAttachment {
  const kind = kindOf(file.name);
  const checked = file.scanned && file.safe;

  return {
    name: file.name,
    size: size(file.bytes),
    kind,
    status: !file.scanned ? 'not checked yet' : file.safe ? 'checked' : 'failed its check',
    origin: file.fromAgent ? 'made by the agent' : 'you provided this',
    warning:
      kind === 'program' ? 'This kind of file can run code — open it with care' : '',
    canPreview: checked && PREVIEWABLE.has(kind),
    canDownload: file.safe,
  };
}

function kindOf(name: string): AttachmentKind {
  // The last extension is the one the system will act on, whatever the
  // friendly-looking one before it says.
  const extension = name.split('.').pop()?.toLowerCase() ?? '';
  return KINDS[extension] ?? 'file';
}

function size(bytes: number): string {
  if (bytes >= 1e6) return `${trim((bytes / 1e6).toFixed(1))} MB`;
  if (bytes >= 1e3) return `${trim((bytes / 1e3).toFixed(1))} kB`;
  return `${bytes} B`;
}

function trim(value: string): string {
  return value.endsWith('.0') ? value.slice(0, -2) : value;
}
