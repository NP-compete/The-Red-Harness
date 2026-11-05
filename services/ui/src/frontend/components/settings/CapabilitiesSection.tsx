import { useSelector } from 'react-redux';

import { resolveCapability, type CapabilityInput, type Scope } from '../../lib/capability';
import type { RootState } from '../../redux/store';

const DECIDED: Record<Scope, string> = {
  deployment: 'set for this deployment',
  agent: 'set for this agent',
  user: 'by you',
};

/** What this agent can do here, and who decided each one. */
export function CapabilitiesSection() {
  const features = useSelector((state: RootState) => state.config.features);
  const debugMode = useSelector((state: RootState) => state.userSettings.debugMode);

  // An empty list and an unloaded one look the same, so nothing is
  // said until the answer is in.
  if (!features) {
    return null;
  }

  const inputs: CapabilityInput[] = [
    { name: 'Memory', deployment: features.memory_enabled },
    { name: 'Connected apps', deployment: features.mcp_apps_enabled },
    {
      name: 'App registration',
      deployment: features.mcp_dcr_enabled,
      requires: [{ name: 'Connected apps', met: !!features.mcp_apps_enabled }],
    },
    { name: 'Debug detail', deployment: features.debug_mode_default, user: debugMode },
    { name: 'Sign-in required', deployment: features.auth_enabled },
  ];

  return (
    <ul className="list-none space-y-2">
      {inputs.map((input) => {
        const capability = resolveCapability(input);
        const decided =
          capability.decidedBy === 'user'
            ? `turned ${capability.enabled ? 'on' : 'off'} by you`
            : DECIDED[capability.decidedBy];

        return (
          <li
            key={capability.name}
            className="flex items-center gap-2 rounded-lg border border-border bg-card p-3"
          >
            <span className="text-sm text-foreground">{capability.name}</span>
            <span
              className={`rounded-full border px-2 py-0.5 text-xs ${
                capability.enabled
                  ? 'border-emerald-500/40 text-emerald-500'
                  : 'border-border text-muted-foreground'
              }`}
            >
              {capability.enabled ? 'On' : 'Off'}
            </span>
            <span className="text-xs text-muted-foreground">
              {capability.blockedBy.length > 0
                ? `needs ${capability.blockedBy.join(', ')}`
                : decided}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
