/**
 * The configuration as a diagram (E34-T1, T2, T3, T4).
 *
 * Not a second source of truth: every box and arrow is derived by the
 * agent from the same tree the editor beside it writes, on each load.
 * Clicking a box opens the file it came from, which is what makes this
 * a view of the configuration rather than a picture of one.
 *
 * Columns are grouped by element kind, and the kinds come from the
 * agent's `element_types` rather than a list here — a kind the tree
 * starts containing shows up with no change to this file.
 *
 * A dangling reference is drawn, not hidden. A subagent naming a skill
 * that no longer exists is the single most useful thing this screen
 * can tell an author, so it gets a ghost box and the reason in words.
 *
 * **Editing is preview-then-save, never save-on-click.** Selecting a
 * box offers the one or two fields the agent will change from here;
 * asking shows what the file would say, and only a second, explicit
 * press writes it. The write carries the version the preview was
 * taken against, so two people editing the same file get a conflict
 * rather than one silently overwriting the other.
 */
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  editFromGraph,
  readConfigFile,
  readConfigGraph,
  type ConfigGraph,
  type GraphNode,
} from '../../services/config-editing-api';

interface Props {
  onOpenFile: (path: string) => void;
}

export function ConfigGraphView({ onOpenFile }: Props) {
  const { t } = useTranslation();
  // `undefined` is "not asked yet" and `null` is "asked and the
  // agent could not say" — drawing the second as the first leaves a
  // spinner on screen for ever on an agent that has no such route.
  const [graph, setGraph] = useState<ConfigGraph | null | undefined>(undefined);
  const [chosen, setChosen] = useState<GraphNode | null>(null);
  const [value, setValue] = useState('');
  const [proposed, setProposed] = useState<{ path: string; content: string } | null>(
    null,
  );
  const [said, setSaid] = useState('');

  const load = useCallback(async () => {
    setGraph(await readConfigGraph());
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const field = chosen?.kind === 'subagent' ? 'model' : 'enabled';

  const ask = useCallback(async () => {
    if (!chosen) return;
    setSaid('');
    const asked =
      field === 'model' ? value.trim() : value !== 'false';
    const answer = await editFromGraph(chosen.id, field, asked, { preview: true });
    if (!answer.ok) {
      setProposed(null);
      setSaid(answer.detail ?? '');
      return;
    }
    setProposed({ path: answer.path ?? '', content: answer.content ?? '' });
  }, [chosen, field, value]);

  const save = useCallback(async () => {
    if (!chosen || !proposed) return;
    // Read the version at save time rather than at preview time: the
    // gap between the two is exactly when somebody else's edit lands,
    // and sending a stale number would turn their change into a
    // conflict the agent reports against the wrong version.
    const file = await readConfigFile(proposed.path);
    const answer = await editFromGraph(
      chosen.id,
      field,
      field === 'model' ? value.trim() : value !== 'false',
      { baseVersion: file?.version },
    );
    if (!answer.ok) {
      setSaid(answer.detail ?? '');
      return;
    }
    setProposed(null);
    setSaid(
      answer.durable === false ? t('configGraph.savedNotDurable') : t('configGraph.saved'),
    );
    // The picture is the point: a change that resolves nothing new,
    // or breaks a reference, should be visible immediately.
    await load();
  }, [chosen, proposed, field, value, load, t]);

  if (graph === undefined) {
    return <p className="text-sm text-muted-foreground">{t('common.loading')}</p>;
  }
  if (graph === null) {
    return (
      <p className="text-sm text-muted-foreground">{t('configGraph.unavailable')}</p>
    );
  }

  const outgoing = (id: string) => graph.edges.filter((e) => e.from === id);

  return (
    <div className="overflow-auto">
      <p className="mb-3 text-xs text-muted-foreground">
        {graph.element_types.map((k) => `${graph.counts[k]} ${k}`).join(' · ')}
      </p>

      {graph.problems.length > 0 && (
        <ul className="mb-4 rounded border border-destructive/50 p-2 text-xs">
          {graph.problems.map((p, i) => (
            <li key={i} className="text-destructive">
              <code>{p.where}</code> — {p.what}
            </li>
          ))}
        </ul>
      )}

      {chosen && (chosen.kind === 'subagent' || chosen.kind === 'mcp') && (
        <div className="mb-4 rounded border border-border p-2">
          <p className="mb-1 text-xs text-muted-foreground">
            {t('configGraph.editing', { label: chosen.label, field })}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {chosen.kind === 'subagent' ? (
              <input
                value={value}
                onChange={(e) => setValue(e.target.value)}
                aria-label={t('configGraph.model')}
                className="w-56 rounded border border-border bg-card px-2 py-1 text-xs"
              />
            ) : (
              <label className="flex items-center gap-1 text-xs">
                <input
                  type="checkbox"
                  checked={value !== 'false'}
                  onChange={(e) => setValue(e.target.checked ? 'true' : 'false')}
                  aria-label={t('configGraph.enabled')}
                />
                {t('configGraph.enabled')}
              </label>
            )}
            <button
              type="button"
              onClick={() => void ask()}
              className="rounded border border-border px-2 py-1 text-xs"
            >
              {t('configGraph.preview')}
            </button>
            {proposed && (
              <button
                type="button"
                onClick={() => void save()}
                className="rounded bg-primary px-2 py-1 text-xs text-primary-foreground"
              >
                {t('configGraph.save')}
              </button>
            )}
          </div>
          {proposed && (
            <>
              <p className="mt-2 text-xs text-muted-foreground">
                {t('configGraph.wouldWrite', { path: proposed.path })}
              </p>
              <pre className="mt-1 max-h-40 overflow-auto rounded bg-muted p-2 text-[0.6875rem]">
                {proposed.content.slice(0, 2000)}
              </pre>
            </>
          )}
          {said && (
            <p className="mt-2 text-xs text-destructive" role="alert">
              {said}
            </p>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-4">
        {graph.element_types.map((kind) => (
          <section key={kind} className="min-w-52">
            <h3 className="mb-1 text-xs font-medium uppercase text-muted-foreground">{kind}</h3>
            <ul className="space-y-1">
              {graph.nodes
                .filter((n) => n.kind === kind)
                .map((n) => {
                  const edges = outgoing(n.id);
                  const broken = edges.filter((e) => e.broken);
                  return (
                    <li key={n.id}>
                      <button
                        type="button"
                        disabled={!n.path}
                        onClick={() => {
                          if (!n.path) return;
                          onOpenFile(n.path);
                          setChosen(n);
                          setProposed(null);
                          setSaid('');
                          setValue(n.kind === 'subagent' ? (n.model ?? '') : 'true');
                        }}
                        title={n.path ?? t('configGraph.notDeclared')}
                        className={`w-full rounded border px-2 py-1 text-left text-xs ${
                          n.missing
                            ? 'border-dashed border-destructive text-destructive'
                            : 'border-border hover:bg-muted'
                        }`}
                      >
                        <span className="block truncate font-medium">{n.label}</span>
                        {n.tier && <span className="text-muted-foreground">{n.tier}</span>}
                        {edges.length > 0 && (
                          <span className="block text-[0.6875rem] text-muted-foreground">
                            {edges.length} →{broken.length > 0 && ` · ${broken.length} broken`}
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
