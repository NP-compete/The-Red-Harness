import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

import { SubagentCurrentStep, SubagentTimeline } from './SubagentTimeline';
import { WRITING, type Step } from '../lib/subagent-steps';

const said = (text?: string): Step => ({
  tool: WRITING,
  id: `${WRITING}-0`,
  startedAt: 1000,
  text,
});

/**
 * The collapsed box shows one line and one line only. A say-step
 * labelled "writing…" there meant the subagent's narration existed in
 * the data and nowhere on screen, so a delegation looked frozen for
 * however long it ran.
 */
describe('the line that stays visible while the box is collapsed', () => {
  it('says what the subagent said, not "writing…"', () => {
    render(<SubagentCurrentStep steps={[said('Checking Datadog for errors first.')]} runningSince={0} />);
    expect(screen.getByText('Checking Datadog for errors first.')).toBeInTheDocument();
    expect(screen.queryByText('subagents.writing')).not.toBeInTheDocument();
  });

  it('falls back to "writing…" only before any text has arrived', () => {
    render(<SubagentCurrentStep steps={[said(undefined)]} runningSince={0} />);
    expect(screen.getByText('subagents.writing')).toBeInTheDocument();
  });

  it('still names a tool when the live step is a call', () => {
    render(
      <SubagentCurrentStep
        steps={[{ tool: 'datadog_search', id: 'a', startedAt: 1000 }]}
        runningSince={0}
      />,
    );
    expect(screen.queryByText('subagents.writing')).not.toBeInTheDocument();
  });
});

describe('the expanded timeline agrees with it', () => {
  it('shows the said text as the step label too', () => {
    render(<SubagentTimeline steps={[said('Now correlating with recent merges.')]} runningSince={0} />);
    expect(screen.getByText('Now correlating with recent merges.')).toBeInTheDocument();
  });
});
