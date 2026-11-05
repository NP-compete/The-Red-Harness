import { useTranslation } from 'react-i18next';
import { useCallback, useEffect, useState } from 'react';
import { FileText, Trash2 } from 'lucide-react';

import { fileSize } from '../../lib/file-size';
import { saySize } from '../../lib/say-size';
import {
  deleteWorkspaceFile,
  listWorkspaceFiles,
  readWorkspaceFile,
  type WorkspaceFile,
} from '../../services/workspace-files';

/** What the agent has written for you, besides what it remembers. */
export function WorkspaceFiles() {
  const { t } = useTranslation();
  const [files, setFiles] = useState<WorkspaceFile[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [contents, setContents] = useState<Record<string, string | null>>({});
  // Asked twice, because a file the agent spent a turn producing is
  // not something to lose to a stray click.
  const [confirming, setConfirming] = useState<string | null>(null);

  const remove = useCallback(async (path: string) => {
    if (confirming !== path) {
      setConfirming(path);
      return;
    }
    setConfirming(null);
    if (await deleteWorkspaceFile(path)) {
      setFiles((had) => (had ?? []).filter((file) => file.path !== path));
    }
  }, [confirming]);

  const show = useCallback(async (path: string) => {
    setOpen((was) => (was === path ? null : path));
    if (path in contents) return;
    const found = await readWorkspaceFile(path);
    setContents((had) => ({ ...had, [path]: found }));
  }, [contents]);

  useEffect(() => {
    let alive = true;
    void listWorkspaceFiles().then((found) => {
      if (alive) setFiles(found);
    });
    return () => {
      alive = false;
    };
  }, []);

  // Nothing is said before the answer is in: an empty workspace and
  // an unasked question look the same otherwise.
  if (files === null) {
    return null;
  }

  if (files.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {t('personal.noFiles')}
      </p>
    );
  }

  return (
    <ul className="list-none space-y-2">
      {files.map((file) => (
        <li
          key={file.path}
          className="flex flex-wrap items-center rounded-lg border border-border bg-card"
        >
          <button
            type="button"
            onClick={() => void show(file.path)}
            aria-expanded={open === file.path}
            className="flex flex-1 items-center gap-2 p-3 text-left transition-colors hover:bg-secondary/30"
          >
            <FileText className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
            <code className="text-sm text-foreground">{file.path}</code>
            <span className="text-xs text-muted-foreground">{saySize(fileSize(file.bytes), t)}</span>
          </button>
          <button
            type="button"
            onClick={() => void remove(file.path)}
            onBlur={() => setConfirming((was) => (was === file.path ? null : was))}
            aria-label={
              confirming === file.path
                ? `Really delete ${file.path}?`
                : `Delete ${file.path}`
            }
            className="px-3 pb-3 text-xs text-muted-foreground transition-colors hover:text-destructive"
          >
            {confirming === file.path ? (
              'Really?'
            ) : (
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            )}
          </button>
          {open === file.path && (
            <div className="w-full border-t border-border p-3">
              {contents[file.path] == null && file.path in contents ? (
                <p className="text-xs text-muted-foreground">
                  {t('personal.unreadable')}
                </p>
              ) : (
                <pre className="whitespace-pre-wrap break-words text-xs text-foreground">
                  {contents[file.path]}
                </pre>
              )}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}
