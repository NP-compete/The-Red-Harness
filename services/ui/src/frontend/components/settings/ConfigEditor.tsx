import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  readConfigFile,
  readConfigTree,
  readEditingState,
  saveConfigFile,
} from '../../services/config-editing-api';
import { ConfigGraphView } from './ConfigGraphView';

/**
 * Changing a configuration file from the browser.
 *
 * What makes this safe to offer is that the agent refuses a
 * change that would not be valid and says which file and which
 * field. So most of the work here is getting out of the way
 * and then reporting that refusal faithfully — a generic
 * "could not save" would send somebody reading their own diff
 * for a problem already located for them.
 *
 * The text shown is the effective one: what the agent reads
 * now, edits included. Showing the mounted file would hand
 * somebody the version they are not running, and their save
 * would quietly discard whatever had been edited since.
 *
 * A read-only deployment gets no editor, rather than one whose
 * save always fails.
 */
export function ConfigEditor() {
  const { t } = useTranslation();
  const [paths, setPaths] = useState<string[]>([]);
  // What the tree actually contains, so the chooser offers files
  // rather than the allowlist's directory prefixes — picking
  // `config/agent/subagents/` was never a file anybody could edit.
  const [uneditable, setUneditable] = useState<string[]>([]);
  const [why, setWhy] = useState('');
  const [filter, setFilter] = useState('');
  // The version loaded with the text, handed back on save (MU-5).
  const [version, setVersion] = useState(0);
  // Where edits go, said before anybody types.
  const [store, setStore] = useState('');
  const [durable, setDurable] = useState(true);
  const [editable, setEditable] = useState<boolean | undefined>(undefined);
  const [chosen, setChosen] = useState('');
  const [draft, setDraft] = useState('');
  const [note, setNote] = useState('');
  const [refused, setRefused] = useState('');
  const [inert, setInert] = useState<{ section: string; decided_by: string }[]>(
    [],
  );

  useEffect(() => {
    let live = true;
    void Promise.all([readEditingState(), readConfigTree()]).then(
      ([state, tree]) => {
        if (!live) return;
        setEditable(state?.editable ?? false);
        setStore(state?.store ?? '');
        setDurable(state?.durable !== false);
        // The tree is the better list. Fall back to the allowlist
        // when the agent is older and has no tree route.
        const fromTree = tree?.files.filter((f) => f.editable).map((f) => f.path);
        const chooseFrom = fromTree?.length ? fromTree : (state?.paths ?? []);
        setPaths(chooseFrom);
        setChosen(chooseFrom[0] ?? '');
        setUneditable(
          tree?.files.filter((f) => !f.editable).map((f) => f.path) ?? [],
        );
        setWhy(tree?.why_not_all ?? '');
      },
    );
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (!chosen) return;
    let live = true;
    void readConfigFile(chosen).then((found) => {
      if (!live || !found) return;
      setDraft(found.content);
      // Zero when the agent did not say: the baseline, which
      // nobody has edited.
      setVersion(found.version ?? 0);
      setInert(found.inert ?? []);
    });
    return () => {
      live = false;
    };
  }, [chosen]);

  const onSave = useCallback(async () => {
    setNote('');
    setRefused('');
    const found = await saveConfigFile(chosen, draft, version);
    if (!found.ok) {
      // What was typed stays in the box. Losing somebody's
      // work because the agent objected to it is a second
      // punishment for one mistake.
      setRefused(found.detail ?? '');
      return;
    }
    // The version moved; hold the new one or this editor's next
    // save conflicts with its own last one.
    if (typeof found.version === 'number') setVersion(found.version);
    setNote(found.durable === false ? t('editor.savedNotDurable') : t('editor.saved'));
  }, [chosen, draft, version, t]);

  if (editable === undefined) return null;

  if (!editable) {
    return (
      <p className="text-sm text-muted-foreground">{t('editor.readOnly')}</p>
    );
  }

  return (
    <section className="mb-12">
      <h2 className="mb-2 text-base font-semibold">{t('editor.heading')}</h2>
      {/* Before the box, not after the save. "This will not survive
          a restart" is the right sentence at the wrong moment once
          somebody has already typed the change. */}
      {!durable && (
        <p className="mb-3 rounded border border-amber-500/60 p-2 text-sm">
          {t('editor.notDurableWarning', { store: store || 'none' })}
        </p>
      )}

      {/* The shape before the text (E34). An author arrives holding
          six files in their head; the diagram says which names
          resolve, and clicking a box picks that file in the chooser
          below — the same tree, read two ways. */}
      <details className="mb-4" open>
        <summary className="cursor-pointer text-sm text-muted-foreground">
          {t('configGraph.heading')}
        </summary>
        <div className="mt-2">
          <ConfigGraphView onOpenFile={(path) => setChosen(`config/agent/${path}`)} />
        </div>
      </details>

      <label className="mb-2 block text-sm" htmlFor="config-path">
        {t('editor.chooseFile')}
      </label>
      {paths.length > 12 && (
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder={t('editor.filter')}
          aria-label={t('editor.filter')}
          className="mb-2 w-full rounded border border-border bg-card px-2 py-1 text-sm"
        />
      )}
      <select
        id="config-path"
        value={chosen}
        onChange={(e) => setChosen(e.target.value)}
        className="mb-3 w-full rounded border border-border bg-card px-2 py-1 text-sm"
      >
        {paths
          .filter((p) => !filter || p.toLowerCase().includes(filter.toLowerCase()))
          .map((path) => (
            <option key={path} value={path}>
              {path}
            </option>
          ))}
      </select>

      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        aria-label={t('editor.editing', { path: chosen })}
        rows={16}
        className="w-full rounded border border-border bg-card p-2 font-mono text-xs"
      />

      {/* Said before the save, not after. This file carries
          sections the file does not drive — the YAML marks them
          `[env-var]` in a comment nobody reading them here can
          see — and an edit to one is stored, versioned and
          reported as drift while the deployment goes on reading
          the environment. */}
      {inert.length > 0 && (
        <div
          className="mt-2 rounded border border-border bg-muted/40 p-2 text-xs"
          role="note"
        >
          <p className="font-medium">{t('editor.inert.title')}</p>
          <ul className="mt-1 space-y-0.5">
            {inert.map((one) => (
              <li key={one.section} className="text-muted-foreground">
                <code>{one.section}</code> — {one.decided_by}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-2 flex items-center gap-3">
        <button
          type="button"
          onClick={() => void onSave()}
          className="rounded bg-primary px-3 py-1 text-sm text-primary-foreground"
        >
          {t('editor.save')}
        </button>
        {note && <span className="text-xs text-muted-foreground">{note}</span>}
      </div>

      {refused && (
        <p className="mt-3 text-xs text-destructive" role="alert">
          {refused}
        </p>
      )}

      {/* Visible but not editable. Listing them is the difference
          between "this deployment has no such file" and "this
          deployment will not let you change it from here". */}
      {uneditable.length > 0 && (
        <details className="mt-4">
          <summary className="cursor-pointer text-sm text-muted-foreground">
            {t('editor.notEditable', { count: uneditable.length })}
          </summary>
          <p className="mt-1 text-xs text-muted-foreground">{why}</p>
          <ul className="mt-2 max-h-48 overflow-auto font-mono text-xs text-muted-foreground">
            {uneditable.map((path) => (
              <li key={path}>{path}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
