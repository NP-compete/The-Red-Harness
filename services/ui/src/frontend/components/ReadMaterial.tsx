import { useTranslation } from 'react-i18next';
import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

import { dedupeReads } from '../lib/dedupe-reads';
import { presentExternalContent } from '../lib/external-content';
import { presentSourceList } from '../lib/duplicate-sources-view';
import { presentResult, type ResultShape, type ResultSummary } from '../lib/tool-result-view';

export interface ReadShape {
  kind: ResultShape;
  rows: number;
  columns: string[];
  language: string;
  needsPaging: boolean;
  needsCollapsing: boolean;
}

export interface ReadItem {
  source: string;
  text: string;
  /** How the agent described this result, when it could. */
  shape?: ReadShape;
}

/**
 * What the turn actually read, on request.
 *
 * Folded away by default: it is the working behind the answer, and
 * unfolding it is the reader's choice. It matters most when a note
 * above says a sentence is not backed by any of it.
 */
/**
 * The words for a result, assembled where there is a translator.
 *
 * A table counts rows and columns independently and a catalogue key
 * carries one count, so the two halves are resolved separately and
 * joined here.
 */
function describeResult(
  summary: ResultSummary,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  switch (summary.kind) {
    case 'empty':
      return t('toolResult.empty', { tool: summary.tool });
    case 'table':
      return `${t('counts.rows', { count: summary.rows })}, ${t('toolResult.columns', {
        count: summary.columns,
      })}`;
    case 'json':
      return t('toolResult.mixed', { count: summary.rows });
    case 'list':
      return t('toolResult.items', { count: summary.rows });
    case 'code':
      return t('toolResult.snippet', { language: summary.language || t('toolResult.code') });
    default:
      return t('toolResult.text');
  }
}

export function ReadMaterial({ read }: { read: ReadItem[] }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  if (read.length === 0) {
    return null;
  }

  const { kept, originals, collapsed } = dedupeReads(read);
  const list = presentSourceList(kept, collapsed);

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => setOpen((on) => !on)}
        aria-expanded={open}
        className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        {/* Counted before folding: the toggle describes the turn, not the list. */}
        {t('counts.readResults', { count: read.length })}
      </button>
      {open && (
        <>
          <ul className="mt-1 list-none space-y-2">
            {list.rows.map((row, index) => {
              const content = presentExternalContent({ source: row.source, text: row.text });
              const shape = originals[index]?.shape;
              const described = shape
                ? presentResult({
                    shape: shape.kind,
                    rows: shape.rows,
                    columns: shape.columns,
                    language: shape.language,
                    needsPaging: shape.needsPaging,
                    needsCollapsing: shape.needsCollapsing,
                    tool: row.source,
                    trusted: false,
                  })
                : null;
              return (
                <li
                  key={`${row.source}-${index}`}
                  className="rounded border border-border/60 bg-secondary/30 p-2"
                >
                  <span className="flex items-baseline gap-2">
                    <span className="text-[11px] font-medium text-muted-foreground">
                      {row.source}
                    </span>
                    {described && (
                      <span className="text-[11px] text-muted-foreground">
                        {describeResult(described.summary, t)}
                      </span>
                    )}
                    {row.agreement && (
                      <span className="text-[11px] text-muted-foreground">{row.agreement}</span>
                    )}
                  </span>
                  <span className="mt-1 block whitespace-pre-wrap text-xs text-foreground/80">
                    {content.preview}
                    {content.collapsed ? '…' : ''}
                  </span>
                  {content.note && (
                    <span className="mt-1 block text-[11px] text-amber-500/80">
                      {content.note}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
          {list.note && (
            <p className="mt-1 text-[11px] text-muted-foreground">{list.note}</p>
          )}
        </>
      )}
    </div>
  );
}
