import { useCallback, useState } from 'react';
import { uploadAttachments, type Attachment } from '../services/attachments-api';
import { getExtractionStatus } from '../services/extraction-status';

interface Options {
  threadId?: string;
  onUploaded?: (attachments: Attachment[], summary: string) => void;
  onError?: (message: string) => void;
}

/**
 * Upload files to a thread, from wherever they arrived.
 *
 * Shared because there are now three ways to hand over a file — the
 * button, a drop, and a paste — and they must behave identically. The
 * last time this logic lived in one component, the other composer
 * shipped without an attach button at all and nobody noticed for
 * weeks.
 */
export function useAttachmentUpload({ threadId, onUploaded, onError }: Options) {
  const [busy, setBusy] = useState(false);

  const upload = useCallback(
    async (files: File[]) => {
      if (!files.length || !threadId) return;
      setBusy(true);
      try {
        // Checked here rather than left to the server: a file over
        // the limit came back as a failed upload, which reads as
        // something going wrong rather than as a file being too big.
        const limit = (await getExtractionStatus())?.maxBytes ?? 0;
        const sending = limit > 0 ? files.filter((f) => f.size <= limit) : files;
        const tooBig = files.filter((f) => !sending.includes(f));

        if (tooBig.length > 0) {
          const mb = (limit / (1024 * 1024)).toFixed(0);
          onError?.(
            `${tooBig.map((f) => f.name).join(', ')} ` +
              `${tooBig.length === 1 ? 'is' : 'are'} over the ${mb} MB limit.`,
          );
        }
        if (sending.length === 0) return;

        const result = await uploadAttachments(threadId, sending);
        onUploaded?.(result.attachments, result.summary);
      } catch (error) {
        onError?.(error instanceof Error ? error.message : 'Upload failed');
      } finally {
        setBusy(false);
      }
    },
    [threadId, onUploaded, onError],
  );

  return { upload, busy };
}

/**
 * The files in a paste, if the paste is a file paste.
 *
 * Returns an empty array for ordinary text so the caller leaves the
 * event alone — a screenshot and a copied paragraph arrive through
 * the same handler, and swallowing the paragraph would break typing.
 */
export function filesFromPaste(event: ClipboardEvent | React.ClipboardEvent): File[] {
  const data = (event as React.ClipboardEvent).clipboardData;
  if (!data) return [];
  const files: File[] = [];
  for (const item of Array.from(data.items ?? [])) {
    if (item.kind !== 'file') continue;
    const file = item.getAsFile();
    if (file) files.push(file);
  }
  return files;
}

/**
 * Whether a drag carries files.
 *
 * Dragging selected text within the page fires the same events, and
 * treating that as an upload puts a full-screen overlay in front of
 * someone who was moving a word.
 */
export function dragHasFiles(event: React.DragEvent | DragEvent): boolean {
  const types = event.dataTransfer?.types;
  if (!types) return false;
  return Array.from(types).includes('Files');
}
