import { useTranslation } from 'react-i18next';

import { presentAttachment } from '../lib/attachment-view';
import type { Attachment } from '../services/attachments-api';

/** One staged file, with what is known about it. */
export function AttachmentChip({ file }: { file: Attachment }) {
  const { t } = useTranslation();

  const presented = presentAttachment({
    name: file.filename,
    bytes: file.bytes,
    // Nothing in this template scans an upload, and saying it was
    // checked would be a claim rather than a fact.
    scanned: false,
    safe: true,
    fromAgent: false,
  });

  return (
    <li className="w-[104px] rounded-xl border border-border bg-secondary/50 p-2.5">
      <span className="block text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
        {presented.kind}
      </span>
      <span className="mt-1.5 block text-xs leading-tight text-foreground line-clamp-2 break-all">
        {presented.name}
      </span>
      <span className="mt-1 block text-[10px] text-muted-foreground">{presented.size}</span>
      {presented.warning && (
        <span className="mt-1 block text-[10px] text-amber-500">{presented.warning}</span>
      )}
      {/* Flagged, because the model is reading a prefix of a document
          the user believes it has in full. */}
      {!file.text_extracted && (
        <span className="mt-1 block text-[10px] text-muted-foreground">
          {t('input.notReadable')}
        </span>
      )}
      {file.truncated && (
        <span className="mt-1 block text-[10px] text-muted-foreground">
          {t('input.truncated')}
        </span>
      )}
      {/* A fallback nobody can see is indistinguishable from the
          thing working. */}
      {file.degraded && (
        <span className="mt-1 block text-[10px] text-muted-foreground" title={file.degraded}>
          {t('input.basicParse')}
        </span>
      )}
    </li>
  );
}
