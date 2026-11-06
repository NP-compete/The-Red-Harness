import { useState } from 'react';
import { Trans, useTranslation } from 'react-i18next';
import { Plus, X, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Turn, ToolCall, ToolCallArg, CaseTag } from './eval-dataset-types';
import { emptyToolCall, normTurn } from './eval-dataset-utils';

interface SingleTurnFormProps {
  name: string;
  tag: CaseTag;
  turn: Turn;
  description: string;
  onNameChange: (v: string) => void;
  onTagChange: (v: CaseTag) => void;
  onTurnChange: (t: Turn) => void;
  onDescriptionChange: (v: string) => void;
}


/** Form for editing a single-turn test case with tag selection, keywords, and optional tool-call expectations. */
export function SingleTurnForm({
  name,
  tag,
  turn,
  description,
  onNameChange,
  onTagChange,
  onTurnChange,
  onDescriptionChange,
}: SingleTurnFormProps) {
  const { t } = useTranslation();
  const [keywordsExpanded, setKeywordsExpanded] = useState(false);

  const isHitl = tag === 'hitl';
  const safeTurn = normTurn(turn);

  /** Merges a partial update into the current turn and propagates via onTurnChange. */
  function updateTurn(patch: Partial<Turn>) {
    onTurnChange({ ...safeTurn, ...patch });
  }

  /** Appends a new empty tool call to the current turn. */
  function addToolCall() {
    updateTurn({ expectedToolCalls: [...safeTurn.expectedToolCalls, emptyToolCall()] });
  }

  /** Removes the tool call at the given index from the current turn. */
  function removeToolCall(i: number) {
    updateTurn({ expectedToolCalls: safeTurn.expectedToolCalls.filter((_, idx) => idx !== i) });
  }

  /** Immutably patches the tool call at the given index. */
  function updateToolCall(i: number, patch: Partial<ToolCall>) {
    const calls = safeTurn.expectedToolCalls.map((tc, idx) => idx === i ? { ...tc, ...patch } : tc);
    updateTurn({ expectedToolCalls: calls });
  }

  /** Appends a new empty argument row to the tool call at the given index. */
  function addArg(toolIdx: number) {
    updateToolCall(toolIdx, {
      arguments: [...safeTurn.expectedToolCalls[toolIdx].arguments, { key: '', value: '' }],
    });
  }

  /** Removes the argument at argIdx from the tool call at toolIdx. */
  function removeArg(toolIdx: number, argIdx: number) {
    updateToolCall(toolIdx, {
      arguments: safeTurn.expectedToolCalls[toolIdx].arguments.filter((_, i) => i !== argIdx),
    });
  }

  /** Immutably patches the argument at argIdx within the tool call at toolIdx. */
  function updateArg(toolIdx: number, argIdx: number, patch: Partial<ToolCallArg>) {
    const args = safeTurn.expectedToolCalls[toolIdx].arguments.map((a, i) =>
      i === argIdx ? { ...a, ...patch } : a,
    );
    updateToolCall(toolIdx, { arguments: args });
  }

  return (
    <div className="space-y-5">
      {/* Name */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-foreground">
          {t('evalCase.caseName')} <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => onNameChange(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
          placeholder={t('evalCase.caseNamePlaceholder')}
          maxLength={20}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30"
        />
        <p className="text-xs text-muted-foreground">{t('evalCase.nameRules')}</p>
      </div>

      {/* Description */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-foreground">
          {t('evalCase.description')} <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder={t('evalCase.descriptionPlaceholder')}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30"
        />
      </div>

      {/* Tag */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-foreground">
          Tag <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-2 gap-3">
          {([
            { value: 'non_hitl' as CaseTag, label: t('evalCase.nonHitl'), desc: t('evalCase.nonHitlDesc') },
            { value: 'hitl' as CaseTag, label: t('evalCase.hitl'), desc: t('evalCase.hitlDesc') },
          ] as { value: CaseTag; label: string; desc: string }[]).map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onTagChange(opt.value)}
              className={cn(
                'text-left rounded-lg border-2 px-4 py-3 transition-colors',
                tag === opt.value
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-muted-foreground/40',
              )}
            >
              <p className="text-sm font-medium text-foreground">{opt.label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{opt.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Query */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-foreground">
          {t('evalCase.userAsks')} <span className="text-red-500">*</span>
        </label>
        <textarea
          value={safeTurn.userMessage}
          onChange={(e) => updateTurn({ userMessage: e.target.value })}
          rows={3}
          placeholder={t('evalCase.userAsksPlaceholder')}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30 resize-y"
        />
      </div>

      {/* Expected response */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-foreground">
          {t('evalCase.agentResponds')} <span className="text-red-500">*</span>
        </label>
        <textarea
          value={safeTurn.expectedResponse}
          onChange={(e) => updateTurn({ expectedResponse: e.target.value })}
          rows={3}
          placeholder={t('evalCase.agentRespondsPlaceholder')}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30 resize-y"
        />
      </div>

      {/* Non-HITL optional fields */}
      {!isHitl && (
        <>
          {/* User intent */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">{t('evalCase.userIntent')}</label>
            <p className="text-xs text-muted-foreground">{t('evalCase.userIntentHelp')}</p>
            <textarea
              value={safeTurn.expectedIntent}
              onChange={(e) => updateTurn({ expectedIntent: e.target.value })}
              rows={2}
              placeholder={t('evalCase.userIntentPlaceholder')}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30 resize-y"
            />
          </div>

          {/* Expected keywords */}
          <div className="space-y-2">
            <button
              type="button"
              onClick={() => setKeywordsExpanded((v) => !v)}
              className="flex items-center gap-2 text-sm font-medium text-foreground hover:text-primary transition-colors"
            >
              {keywordsExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              {t('evalCase.expectedKeywords')}<span className="text-xs font-normal text-muted-foreground">{t('evalCase.optional')}</span>
              {safeTurn.expectedKeywords.filter(Boolean).length > 0 && (
                <span className="text-xs font-medium text-primary">
                  {t('counts.rows', { count: safeTurn.expectedKeywords.filter(Boolean).length })}
                </span>
              )}
            </button>

            {keywordsExpanded && (
              <div className="space-y-2 pl-2 border-l-2 border-border">
                <p className="text-xs text-muted-foreground">
                  {t('evalCase.rowIsOption')} <strong>option</strong>{t('evalCase.keywordRowsExplainer')}</p>
                <p className="text-xs text-muted-foreground/70">
                  {t('evalCase.toCheck')} <em>{t('evalCase.twoRowsExample')}</em>{t('evalCase.useTwoRows')} <code className="font-mono">A, B</code> and <code className="font-mono">A, C</code>.
                </p>
                {safeTurn.expectedKeywords.map((row, ri) => (
                  <div key={ri} className="flex items-center gap-2">
                    <input
                      type="text"
                      value={row}
                      onChange={(e) => {
                        const next = [...safeTurn.expectedKeywords];
                        next[ri] = e.target.value;
                        updateTurn({ expectedKeywords: next });
                      }}
                      placeholder={t('evalCase.keywordsOrPlaceholder')}
                      className="flex-1 rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                    />
                    {safeTurn.expectedKeywords.length > 1 && (
                      <button
                        type="button"
                        onClick={() => updateTurn({ expectedKeywords: safeTurn.expectedKeywords.filter((_, i) => i !== ri) })}
                        className="text-muted-foreground hover:text-red-500"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => updateTurn({ expectedKeywords: [...safeTurn.expectedKeywords, ''] })}
                  className="text-xs text-primary hover:underline flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" /> {t('evalCase.addAndRow')}
                </button>
              </div>
            )}
          </div>

          {/* Expected tool calls (Actions) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-foreground">{t('evalCase.expectedToolCalls')} <span className="text-muted-foreground font-normal">{t('evalCase.actionsTag')}</span></label>
                <p className="text-xs text-muted-foreground">{t('evalCase.expectedToolCallsHelp')}</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer gap-2">
                <input
                  type="checkbox"
                  checked={safeTurn.toolCallEnabled}
                  onChange={(e) => {
                    updateTurn({
                      toolCallEnabled: e.target.checked,
                      expectedToolCalls: e.target.checked && safeTurn.expectedToolCalls.length === 0
                        ? [emptyToolCall()]
                        : safeTurn.expectedToolCalls,
                    });
                  }}
                  className="sr-only"
                />
                <div className={cn(
                  'w-9 h-5 rounded-full transition-colors',
                  safeTurn.toolCallEnabled ? 'bg-primary' : 'bg-border',
                )}>
                  <div className={cn(
                    'w-3.5 h-3.5 rounded-full bg-white shadow transition-transform mt-0.5 mx-0.5',
                    safeTurn.toolCallEnabled ? 'translate-x-4' : 'translate-x-0',
                  )} />
                </div>
                <span className="text-sm text-muted-foreground">
                  {safeTurn.toolCallEnabled ? 'ON' : 'OFF'}
                </span>
              </label>
            </div>

            {safeTurn.toolCallEnabled && (
              <div className="space-y-3">
                {/* Ordered toggle */}
                <label className="flex items-center gap-2 cursor-pointer text-sm text-muted-foreground select-none">
                  <input
                    type="checkbox"
                    checked={safeTurn.toolCallOrdered}
                    onChange={(e) => updateTurn({ toolCallOrdered: e.target.checked })}
                    className="w-4 h-4 accent-primary cursor-pointer"
                  />
                  {t('evalCase.exactOrder')}
                  <span className="text-muted-foreground/60 text-xs">{t('evalCase.defaultAnyOrder')}</span>
                </label>

                {safeTurn.expectedToolCalls.map((tc, ti) => (
                  <div key={ti} className="rounded-lg border border-border bg-secondary/20 p-4 space-y-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        Tool {ti + 1}
                      </span>
                      {safeTurn.expectedToolCalls.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeToolCall(ti)}
                          className="ml-auto text-muted-foreground hover:text-red-500"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                    <input
                      type="text"
                      value={tc.toolName}
                      onChange={(e) => updateToolCall(ti, { toolName: e.target.value })}
                      placeholder={t('evalCase.toolNamePlaceholder')}
                      className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm font-mono placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30"
                    />
                    <div className="space-y-1.5">
                      <p className="text-xs text-muted-foreground">
                        <Trans
                          i18nKey="evalCase.argumentsHelp"
                          components={[
                            <span key="0" />,
                            <span key="1" className="text-muted-foreground/60" />,
                            <span key="2" />,
                            <code key="3" className="font-mono" />,
                          ]}
                        />
                      </p>
                      {tc.arguments.map((arg, ai) => (
                        <div key={ai} className="flex items-center gap-2">
                          <input
                            type="text"
                            value={arg.key}
                            onChange={(e) => updateArg(ti, ai, { key: e.target.value })}
                            placeholder={t('evalCase.keyPlaceholder')}
                            className="w-32 rounded-md border border-border bg-background px-2 py-1 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-primary/30"
                          />
                          <span className="text-muted-foreground text-xs">:</span>
                          <input
                            type="text"
                            value={arg.value}
                            onChange={(e) => updateArg(ti, ai, { value: e.target.value })}
                            placeholder={t('evalCase.valuePlaceholder')}
                            className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-primary/30"
                          />
                          {tc.arguments.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeArg(ti, ai)}
                              className="text-muted-foreground hover:text-red-500"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      ))}
                      <button
                        type="button"
                        onClick={() => addArg(ti)}
                        className="text-xs text-primary hover:underline flex items-center gap-1"
                      >
                        <Plus className="w-3 h-3" /> {t('evalCase.addArgument')}
                      </button>
                    </div>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addToolCall}
                  className="w-full rounded-lg border border-dashed border-border py-2 text-sm text-muted-foreground hover:border-primary hover:text-primary transition-colors flex items-center justify-center gap-2"
                >
                  <Plus className="w-4 h-4" /> {t('evalCase.addToolCall')}
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
