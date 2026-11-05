import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { FeatureList } from './FeatureList';
import * as api from '../../services/features-api';

const planner = {
  key: 'planner_enabled',
  enabled: false,
  scope: 'agent' as const,
  decided_by: 'default',
  overruled: false,
  missing: [],
  cost: 'Adds a planning model call to every request',
};

function answering(features: unknown[], unreadable = false) {
  return vi
    .spyOn(api, 'readFeatures')
    .mockResolvedValue({ features, unreadable } as never);
}

describe('FeatureList', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('names each declared capability', async () => {
    answering([planner]);
    render(<FeatureList />);
    expect(await screen.findByText(/planner/i)).toBeInTheDocument();
  });

  it('says what turning one on costs', async () => {
    answering([planner]);
    render(<FeatureList />);
    expect(
      await screen.findByText(/Adds a planning model call/),
    ).toBeInTheDocument();
  });

  it('says where the capability may be set', async () => {
    answering([planner]);
    render(<FeatureList />);
    expect(await screen.findByText(/agent/i)).toBeInTheDocument();
  });

  it('tells a capability waiting on another apart from one just off', async () => {
    answering([{ ...planner, missing: ['sandbox_backend'] }]);
    render(<FeatureList />);
    expect(await screen.findByText(/sandbox_backend/)).toBeInTheDocument();
  });

  it('says when something above it refused', async () => {
    answering([{ ...planner, overruled: true, decided_by: 'deployment' }]);
    render(<FeatureList />);
    expect(await screen.findByText(/deployment/i)).toBeInTheDocument();
  });

  it('says when the declarations could not be read', async () => {
    // Silence here reads as "no capabilities", which is a different
    // and much more comfortable thing than "nobody could tell".
    answering([], true);
    render(<FeatureList />);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('says plainly when a deployment declares none', async () => {
    answering([]);
    render(<FeatureList />);
    await waitFor(() =>
      expect(screen.getByText(/no optional capabilities/i)).toBeInTheDocument(),
    );
  });

  it('does not claim anything while it is still asking', () => {
    vi.spyOn(api, 'readFeatures').mockReturnValue(new Promise(() => {}) as never);
    render(<FeatureList />);
    expect(screen.queryByText(/no optional capabilities/i)).not.toBeInTheDocument();
  });
});

describe('FeatureList, turning one on', () => {
  const swarm = {
    key: 'swarm_enabled',
    enabled: false,
    scope: 'deployment' as const,
    decided_by: 'default',
    overruled: false,
    missing: [],
    cost: 'multiplies model spend',
  };

  beforeEach(() => vi.restoreAllMocks());

  it('offers a switch for a capability this level may set', async () => {
    answering([swarm]);
    render(<FeatureList />);
    expect(await screen.findByRole('switch')).toBeInTheDocument();
  });

  it('offers none for a capability set in the configuration tree', async () => {
    // An agent-scoped flag is shown, read-only. A switch that posts
    // and is refused is worse than no switch.
    answering([{ ...planner, scope: 'agent' as const }]);
    render(<FeatureList />);
    await screen.findByText(/planner/i);
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
  });

  it('offers none while a precondition is missing', async () => {
    answering([{ ...swarm, missing: ['sandbox_backend'] }]);
    render(<FeatureList />);
    await screen.findByText(/sandbox_backend/);
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
  });

  it('asks the agent to turn it on', async () => {
    answering([swarm]);
    const wrote = vi
      .spyOn(api, 'writeFeature')
      .mockResolvedValue({ ok: true } as never);
    render(<FeatureList />);
    (await screen.findByRole('switch')).click();
    await waitFor(() => expect(wrote).toHaveBeenCalledWith('swarm_enabled', true));
  });

  it('says so when the agent refused', async () => {
    // The endpoint enforces the rules; the reason it gives is the
    // only thing that explains a switch snapping back.
    answering([swarm]);
    vi.spyOn(api, 'writeFeature').mockResolvedValue({
      ok: false,
      reason: 'swarm_enabled needs sandbox_backend first',
    } as never);
    render(<FeatureList />);
    (await screen.findByRole('switch')).click();
    expect(await screen.findByText(/needs sandbox_backend/)).toBeInTheDocument();
  });

  it('leaves the switch where it was when the agent refused', async () => {
    answering([swarm]);
    vi.spyOn(api, 'writeFeature').mockResolvedValue({
      ok: false,
      reason: 'no',
    } as never);
    render(<FeatureList />);
    const toggle = await screen.findByRole('switch');
    toggle.click();
    await waitFor(() => expect(toggle).not.toBeChecked());
  });
});

describe('FeatureList, a capability that cannot be turned on yet', () => {
  beforeEach(() => vi.restoreAllMocks());

  const blocked = {
    key: 'browser_automation_enabled',
    enabled: false,
    scope: 'deployment' as const,
    decided_by: 'default',
    overruled: false,
    missing: ['sandbox_backend'],
    cost: 'renders pages the agent did not write',
  };

  it('offers no switch, before anybody reaches for one', async () => {
    // The agent would refuse this. Relaying that refusal afterwards
    // is worse than never offering the switch.
    answering([blocked]);
    render(<FeatureList />);
    await screen.findByText(/sandbox_backend/);
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
  });

  it('says what has to come first', async () => {
    answering([blocked]);
    render(<FeatureList />);
    expect(await screen.findByText(/Waiting on: sandbox_backend/)).toBeInTheDocument();
  });

  it('offers one for the precondition itself', async () => {
    answering([
      blocked,
      {
        key: 'sandbox_backend',
        enabled: false,
        scope: 'deployment' as const,
        decided_by: 'default',
        overruled: false,
        missing: [],
        cost: 'runs an isolated environment',
      },
    ]);
    render(<FeatureList />);
    expect(await screen.findByRole('switch')).toHaveAccessibleName('sandbox_backend');
  });
});
