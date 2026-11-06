import { useState } from 'react';
import { ExpandableSection, Label } from '@patternfly/react-core';

import { presentToolActivity } from '../lib/tool-activity';
import type { RecordedCall } from '../lib/tool-calls';
import { useTranslation } from 'react-i18next';

export interface McpStatusPanelProps {
  readonly mcpEvents: ReadonlyArray<{ readonly tool: string; readonly status: string; readonly timestamp: number }>;
  /** Tool calls recorded from the stream, which is where the detail comes from. */
  readonly toolCalls?: ReadonlyArray<RecordedCall>;
}

function labelColorForStatus(status: string): 'blue' | 'green' | 'red' {
  const s = status.toLowerCase();
  if (s === 'success' || s === 'completed' || s === 'ok') {
    return 'green';
  }
  if (s === 'error' || s === 'failed') {
    return 'red';
  }
  if (
    s === 'calling' ||
    s === 'pending' ||
    s === 'running' ||
    s === 'in_progress' ||
    s === 'in progress'
  ) {
    return 'blue';
  }
  return 'blue';
}

export function McpStatusPanel({ mcpEvents, toolCalls = [] }: McpStatusPanelProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(true);

  // Either channel will do: the status events, or the calls the browser
  // recorded from the stream itself.
  if (mcpEvents.length === 0 && toolCalls.length === 0) {
    return null;
  }

  const activity = presentToolActivity(
    toolCalls.map((call) => ({
      tool: call.tool,
      state: call.state,
      ms: call.ms,
      writes: call.writes,
    })),
  );

  return (
    <div className="max-w-3xl mx-auto px-3 pt-2" role="region" aria-label={t('mcp.toolStatus')}>
      <ExpandableSection
        toggleText="MCP tool activity"
        isExpanded={expanded}
        onToggle={(_e, isExpanded) => setExpanded(isExpanded)}
        isIndented
        className="mb-2"
      >
        <ul className="list-none m-0 p-0 space-y-2">
          {mcpEvents.map((evt, idx) => (
            <li
              key={`${evt.tool}-${evt.timestamp}-${idx}`}
              className="flex flex-wrap items-center gap-2 text-sm"
            >
              <span className="font-mono text-xs text-foreground">{evt.tool}</span>
              <Label color={labelColorForStatus(evt.status)} isCompact>
                {evt.status}
              </Label>
            </li>
          ))}
        </ul>
        {toolCalls.length > 0 && (
          <div className="mt-1 space-y-0.5">
            {activity.summary && (
              <p className="text-[11px] text-muted-foreground">{activity.summary}</p>
            )}
            <ul className="list-none m-0 p-0">
              {activity.steps.map((step, index) => (
                <li
                  key={`${step.tool}-${index}`}
                  className="flex items-baseline justify-between gap-3 text-[11px]"
                >
                  <span className="text-foreground">{step.tool}</span>
                  <span className="text-muted-foreground">{step.took}</span>
                </li>
              ))}
            </ul>
            {activity.slowest && (
              <p className="text-[11px] text-muted-foreground">{activity.slowest}</p>
            )}
            {activity.changing > 0 && (
              <p className="text-[11px] text-amber-500/90">
                {activity.changing} changed something
              </p>
            )}
          </div>
        )}
      </ExpandableSection>
    </div>
  );
}
