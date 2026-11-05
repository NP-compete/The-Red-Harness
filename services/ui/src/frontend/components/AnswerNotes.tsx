import { useTranslation } from 'react-i18next';
import { AlertTriangle } from 'lucide-react';

import { presentBudget, type BudgetState } from '../lib/budget-view';
import { presentConfidence, type Stance } from '../lib/confidence-view';
import { presentCoverage, type CoverageState } from '../lib/coverage-view';
import { Followups } from './Followups';
import { presentLoop, type LoopState } from '../lib/loop-warning-view';
import { presentNumericCheck } from '../lib/numeric-check-view';
import { presentQuote, type QuoteState } from '../lib/quote-view';

import type { CitationRecord } from '../lib/citation-view';
import type { SearchedRecord } from '../lib/searched-view';

export interface AnswerNotesData {
  stance?: Stance;
  hedge?: string;
  concerns?: string[];
  figures?: {
    checked: number;
    unsupported: string[];
  };
  loop?: LoopState;
  /** Tools a spent call budget took away before this answer. */
  budget?: BudgetState;
  coverage?: CoverageState;
  /** Documents the answer borrowed from. Rendered separately. */
  citations?: CitationRecord[];
  /**
   * Documents the search weighed, used or not, with how well
   * each matched. Separate from `citations`, which is what the
   * answer borrowed from: this is what it considered.
   */
  retrieval?: SearchedRecord[];
  /**
   * Servers whose text this answer repeats. Named so a reader
   * can judge material nobody here wrote or reviewed.
   */
  from_outside?: string[];
  claims?: {
    text: string;
    supported: boolean;
    contradicted: boolean;
    /** The closest passage in what was read, when there is one. */
    nearest?: QuoteState | null;
  }[];
  /** Material that was written to be obeyed rather than read. */
  injection?: { signals: string[]; evidence: string[] };
}

/** What the answer rests on, said only when some of it rests on nothing. */
export function AnswerNotes({
  notes,
  onAsk,
}: {
  notes?: AnswerNotesData;
  onAsk?: (question: string) => void;
}) {
  const { t } = useTranslation();
  if (!notes) {
    return null;
  }

  const confidence = notes.stance
    ? presentConfidence({
        stance: notes.stance,
        hedge: notes.hedge ?? '',
        concerns: notes.concerns ?? [],
        whatWouldHelp: '',
      })
    : null;

  const figures = notes.figures
    ? presentNumericCheck({
        checked: notes.figures.checked,
        unsupported: notes.figures.unsupported,
      })
    : null;

  const loop = notes.loop ? presentLoop(notes.loop) : null;
  const budget = presentBudget(notes.budget);
  const coverage = notes.coverage ? presentCoverage(notes.coverage) : null;
  const claims = notes.claims ?? [];
  const planted = notes.injection;
  const contradicted = claims.filter((claim) => claim.contradicted).length;

  if (
    !confidence &&
    !figures &&
    !loop &&
    !budget &&
    !coverage &&
    !planted &&
    claims.length === 0
  ) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="mt-1 space-y-0.5 text-xs text-amber-500/90"
    >
      {confidence && (
        <div className="flex items-start gap-1.5">
          <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" />
          <span>
            {confidence.headline}
            {confidence.concerns.length > 0 && (
              <span className="ml-1 text-muted-foreground">
                {confidence.concerns.join('; ')}
              </span>
            )}
          </span>
        </div>
      )}
      {planted && (
        <div className="flex items-start gap-1.5">
          <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" />
          <span>
            {t('answerNotes.plantedInstruction')}
            <span className="ml-1 block text-muted-foreground">
              {planted.evidence.map((quote) => (
                <span key={quote} className="block">
                  {`\u201C${quote}\u201D`}
                </span>
              ))}
            </span>
          </span>
        </div>
      )}
      {claims.length > 0 && (
        <div className="flex items-start gap-1.5">
          <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" />
          <span>
            {t(
              contradicted > 0
                ? 'answerNotes.contradicted'
                : 'answerNotes.unsupported',
              { count: claims.length },
            )}
            <span className="ml-1 block text-muted-foreground">
              {claims.map((claim) => {
                const nearest = presentQuote(claim.nearest ?? null);
                return (
                  <span key={claim.text} className="block">
                    {`\u201C${claim.text}\u201D`}
                    {/* A paraphrase and an invention both flag; the
                        closest passage read is what tells them apart. */}
                    {nearest && (
                      <span className="block pl-3 text-muted-foreground">
                        {`closest: \u201C${nearest.text}\u201D \u2014 ${nearest.source}`}
                        {nearest.note && ` (${nearest.note})`}
                      </span>
                    )}
                  </span>
                );
              })}
            </span>
          </span>
        </div>
      )}
      {coverage && (
        <div className="flex items-start gap-1.5">
          <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" />
          <span>
            {t(coverage.headline, { count: coverage.headlineCount })}
            {coverage.parts.length > 0 && (
              <span className="ml-1 text-muted-foreground">{coverage.parts.join('; ')}</span>
            )}
            {onAsk && <Followups uncovered={coverage.parts} onAsk={onAsk} />}
          </span>
        </div>
      )}
      {loop && (
        <div className="flex items-start gap-1.5">
          <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" />
          <span>
            {loop.headline}
            <span className="ml-1 text-muted-foreground">{loop.detail}</span>
          </span>
        </div>
      )}
      {budget && (
        <div className="flex items-start gap-1.5">
          <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" />
          <span>
            {budget.headline}
            <span className="ml-1 text-muted-foreground">{budget.detail}</span>
          </span>
        </div>
      )}
      {figures && (
        <div className="flex items-start gap-1.5">
          <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" />
          <span>
            {figures.warning}
            <span className="ml-1 text-muted-foreground">{figures.detail}</span>
          </span>
        </div>
      )}
    </div>
  );
}
