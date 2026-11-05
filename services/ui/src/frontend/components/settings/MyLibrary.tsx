import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, Pencil, Trash2 } from 'lucide-react';

import { describeLibrary, type LibraryReport } from '../../lib/document-view';
import {
  addToLibrary,
  editInLibrary,
  readDocument,
  readLibrary,
  removeFromLibrary,
  rewriteSelection,
} from '../../services/knowledge-api';

/**
 * A person's own documents in the retrieval library.
 *
 * Not the shared volume: that one is a single capacity for the
 * whole deployment, writable only by a privileged role, and
 * lives behind the developer gate. These are personal, and
 * every user has them — which is why they cannot share a page.
 *
 * Shown only when the deployment keeps personal documents at
 * all. An upload box in front of a scope retrieval will never
 * search is the defect this area exists to avoid.
 */
export function MyLibrary() {
  const { t } = useTranslation();
  const [report, setReport] = useState<LibraryReport | null | undefined>(undefined);
  const [title, setTitle] = useState('');
  const [text, setText] = useState('');
  const [refused, setRefused] = useState('');
  // Which note is open, and what it currently says. Loaded on
  // demand: the list carries titles and sizes and never
  // bodies, which is right and means the text has to be asked
  // for when somebody wants to change it.
  const [editing, setEditing] = useState<{ id: string; title: string } | null>(null);
  const [draft, setDraft] = useState('');
  // What to do with the highlighted passage, and whether a
  // request for it is in flight. The passage itself is not kept
  // here: it is read off the box when the button is pressed, so
  // what goes is what is highlighted at that moment rather than
  // whatever was highlighted when some earlier render happened.
  const [instruction, setInstruction] = useState('');
  const [rewriting, setRewriting] = useState(false);
  const box = useRef<HTMLTextAreaElement | null>(null);


  const reload = useCallback(async () => {
    setReport(await readLibrary());
  }, []);

  const onEdit = useCallback(
    async (id: string, title: string) => {
      setRefused('');
      const found = await readDocument(id);
      if (!found) {
        setRefused(t('library.couldNotOpen'));
        return;
      }
      setEditing({ id, title: found.title });
      setDraft(found.text);
    },
    [t],
  );

  const onSave = useCallback(async () => {
    if (!editing) return;
    const saved = await editInLibrary(editing.id, editing.title, draft.trim());
    if (!saved.ok) {
      // The agent's own words: it knows how much room is left
      // and whose note this is.
      setRefused('detail' in saved ? (saved.detail ?? '') : '');
      return;
    }
    setEditing(null);
    setDraft('');
    await reload();
  }, [editing, draft, reload, t]);

  const onRewrite = useCallback(async () => {
    const area = box.current;
    if (!area || !instruction.trim()) return;

    const from = area.selectionStart ?? 0;
    const to = area.selectionEnd ?? 0;
    const selected = draft.slice(from, to);
    if (!selected.trim()) {
      // Deliberately not "rewrite the whole note instead". That
      // is a different and much more destructive action to
      // arrive at by pressing the same button.
      setRefused(t('library.selectFirst'));
      return;
    }

    setRefused('');
    setRewriting(true);
    const found = await rewriteSelection(selected, instruction.trim());
    setRewriting(false);

    if (!found.ok) {
      setRefused(found.reason);
      return;
    }
    // Into the box, not into the note. Until save is pressed
    // this is undoable, which is what makes it safe to offer.
    setDraft(draft.slice(0, from) + found.text + draft.slice(to));
    setInstruction('');
  }, [draft, instruction, t]);

  useEffect(() => {
    let live = true;
    void readLibrary().then((found) => {
      if (live) setReport(found);
    });
    return () => {
      live = false;
    };
  }, []);

  // Still asking. Nothing to say yet, and a flicker of "not
  // available" before the answer arrives would be worse than a
  // blank moment.
  if (report === undefined) return null;

  const described = describeLibrary(report);
  if (!described) {
    // The section is listed whatever the deployment keeps, so
    // rendering nothing leaves a heading with empty space under
    // it — a reader cannot tell "off" from "broken" from "still
    // loading". The agent answers 404 here because the feature is
    // absent rather than refused, and that is worth one sentence.
    return (
      <p className="text-sm text-muted-foreground">{t('library.notKept')}</p>
    );
  }

  const onAdd = async () => {
    setRefused('');
    // Never sent. It would always fit and is never worth
    // storing, and the agent would refuse it anyway.
    if (!text.trim()) return;

    const found = await addToLibrary(title.trim(), text.trim());
    if (found.ok === false) {
      setRefused(found.detail ?? t('library.addFailed'));
      return;
    }
    setTitle('');
    setText('');
    await reload();
  };

  const onRemove = async (id: string) => {
    // Only when the agent says it is gone. Dropping it from the
    // list regardless would say it is gone when it is not.
    if (await removeFromLibrary(id)) await reload();
  };

  return (
    <div>
      <p className="mb-3 text-sm text-muted-foreground">{t('library.description')}</p>

      {described.documents.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t('library.empty')}</p>
      ) : (
        <>
        {editing && (
          <div className="mb-4 rounded border border-border p-3">
            <p className="mb-2 text-sm font-medium">
              {t('library.editing', { title: editing.title })}
            </p>
            <textarea
              ref={box}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              aria-label={t('library.editing', { title: editing.title })}
              rows={6}
              className="w-full rounded border border-border bg-card p-2 text-sm"
            />
            <div className="mt-2 flex gap-2">
              <input
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                aria-label={t('library.whatToChange')}
                placeholder={t('library.whatToChangePlaceholder')}
                className="flex-1 rounded border border-border bg-card px-2 py-1 text-sm"
              />
              <button
                type="button"
                onClick={() => void onRewrite()}
                disabled={rewriting}
                className="rounded border border-border px-3 py-1 text-sm disabled:opacity-50"
              >
                {rewriting ? t('library.rewriting') : t('library.rewriteSelection')}
              </button>
            </div>
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                onClick={() => void onSave()}
                className="rounded bg-primary px-3 py-1 text-sm text-primary-foreground"
              >
                {t('library.save')}
              </button>
              <button
                type="button"
                onClick={() => { setEditing(null); setRefused(''); }}
                className="rounded border border-border px-3 py-1 text-sm"
              >
                {t('library.cancel')}
              </button>
            </div>
          </div>
        )}
        <ul className="mb-4 space-y-1">
          {described.documents.map((document) => (
            <li
              key={document.id}
              className="flex items-center justify-between rounded border border-border px-3 py-2"
            >
              <span className="text-sm">{document.title}</span>
              <span className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground">{document.size}</span>
                <button
                  type="button"
                  onClick={() => void onEdit(document.id, document.title)}
                  aria-label={t('library.edit', { title: document.title })}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <Pencil className="h-4 w-4" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  onClick={() => void onRemove(document.id)}
                  aria-label={t('library.remove', { title: document.title })}
                  className="text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </button>
              </span>
            </li>
          ))}
        </ul>
        </>
      )}

      {described.shared.length > 0 ? (
        <div className="mb-4">
          <p className="mb-1 text-xs text-muted-foreground">
            {t('library.sharedHeading')}
          </p>
          <ul className="space-y-1">
            {described.shared.map((document) => (
              <li
                key={document.id}
                className="flex items-center justify-between rounded border border-border px-3 py-2"
              >
                <span className="text-sm">{document.title}</span>
                <span className="flex items-center gap-3 text-xs text-muted-foreground">
                  {/* No remove button: it comes from the
                      configuration tree and returns on the
                      next sync. */}
                  <span>{document.team}</span>
                  <span>{document.size}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className="text-xs text-muted-foreground">
        {t('library.used', {
          used: described.usedLabel,
          limit: described.limitLabel,
        })}
      </p>
      {described.nearlyFull ? (
        <p role="status" className="mt-1 flex items-center gap-1 text-xs text-amber-500">
          <AlertTriangle className="h-3 w-3 shrink-0" aria-hidden="true" />
          {t('library.nearlyFull')}
        </p>
      ) : null}

      <div className="mt-4 space-y-2">
        <label className="block text-xs text-muted-foreground" htmlFor="library-title">
          {t('library.titleLabel')}
        </label>
        <input
          id="library-title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="w-full rounded border border-border bg-background px-2 py-1 text-sm"
        />
        <label className="block text-xs text-muted-foreground" htmlFor="library-text">
          {t('library.textLabel')}
        </label>
        <textarea
          id="library-text"
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={4}
          className="w-full rounded border border-border bg-background px-2 py-1 text-sm"
        />
        <button
          type="button"
          onClick={() => void onAdd()}
          className="rounded bg-primary px-3 py-1 text-sm text-primary-foreground"
        >
          {t('library.add')}
        </button>
        {refused ? (
          <p role="alert" className="text-xs text-destructive">
            {refused}
          </p>
        ) : null}
      </div>
    </div>
  );
}
