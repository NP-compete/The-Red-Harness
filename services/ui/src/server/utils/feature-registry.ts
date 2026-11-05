/**
 * What each feature flag is, who decides it, and what it changes.
 *
 * The flags themselves already existed, read in whichever file
 * needed them. Ten booleans read in ten places is fine until one is
 * read in two places with different defaults, and then it is a bug
 * nobody can see — so they are declared once, here, and the
 * interface reports the effective value with the level that decided
 * it. A switch whose value came from somewhere else is worse than no
 * switch, because it looks answerable.
 */

export type Scope = "deployment" | "agent" | "user";
export type Source = "default" | "configuration file" | "environment" | "set here";

export interface Flag {
  key: string;
  scope: Scope;
  /** What changes when it is on, in one line. */
  effect: string;
  /** Environment variables that decide it, most current first. */
  env: string[];
  /** Whether an operator may see it at all. */
  uiExposed: boolean;
}

export interface DescribedFlag extends Flag {
  value: boolean;
  source: Source;
  /** The environment variable that decided it, when one did. */
  setBy?: string;
  /** Whether an operator may change it from here. */
  overridable: boolean;
}

const FLAGS: Flag[] = [
  {
    key: "auth_enabled",
    scope: "deployment",
    effect: "Requires people to sign in, and scopes everything to who they are.",
    env: ["FEATURE_AUTH_ENABLED", "AUTH_ENABLED"],
    uiExposed: true,
  },
  {
    key: "memory_enabled",
    scope: "deployment",
    effect: "Lets the agent keep notes about a person between conversations.",
    env: [],
    uiExposed: true,
  },
  {
    key: "debug_mode_default",
    scope: "user",
    effect: "Starts everyone in developer mode rather than leaving it to them.",
    env: ["FEATURE_DEBUG_MODE_DEFAULT"],
    uiExposed: true,
  },
  {
    key: "mcp_dcr_enabled",
    scope: "deployment",
    effect: "Lets the agent register itself with outside servers that ask it to.",
    env: ["MCP_DCR_ENABLED"],
    uiExposed: true,
  },
  {
    key: "mcp_apps_enabled",
    scope: "deployment",
    effect: "Renders interfaces supplied by outside servers, inside a sandbox.",
    env: ["FEATURE_MCP_APPS_ENABLED"],
    uiExposed: true,
  },
  {
    key: "skills_visible_to_all",
    scope: "deployment",
    effect: "Shows what the agent knows how to do to everyone, not only operators.",
    env: [],
    uiExposed: true,
  },
  {
    key: "subagents_visible_to_all",
    scope: "deployment",
    effect: "Shows who the agent delegates to, to everyone.",
    env: [],
    uiExposed: true,
  },
  {
    key: "prompt_visible_to_all",
    scope: "deployment",
    effect: "Shows the agent's own instructions to everyone.",
    env: [],
    uiExposed: true,
  },
  {
    key: "models_visible_to_all",
    scope: "deployment",
    effect: "Shows which models answer, to everyone.",
    env: [],
    uiExposed: true,
  },
  {
    key: "safeguards_visible_to_all",
    scope: "deployment",
    effect: "Shows which checks run on an answer, to everyone.",
    env: [],
    uiExposed: true,
  },
];

export const REGISTRY: Record<string, Flag> = Object.fromEntries(
  FLAGS.map((flag) => [flag.key, flag]),
);

function fromEnv(flag: Flag, env: Record<string, string | undefined>) {
  for (const name of flag.env) {
    if (env[name] !== undefined) return { name, value: env[name] === "true" };
  }
  return null;
}

/**
 * Every flag an operator may see, with the level that decided it.
 *
 * Only declared flags appear: a value in the settings with no flag
 * behind it is not a feature anyone chose, and a flag declared
 * hidden is absent rather than merely unrendered.
 */
export function describeFeatures(
  defaults: Record<string, unknown>,
  fromFile: Record<string, unknown>,
  env: Record<string, string | undefined>,
  setHere: Record<string, boolean> = {},
  overridable: readonly string[] = [],
): DescribedFlag[] {
  return Object.values(REGISTRY)
    .filter((flag) => flag.uiExposed)
    .sort((a, b) => a.key.localeCompare(b.key))
    .map((flag) => {
      const base = { ...flag, overridable: overridable.includes(flag.key) };

      // Highest first, and this order is the one the server actually
      // applies: what an operator set here is merged over everything
      // when the settings are read.
      if (flag.key in setHere) {
        return { ...base, value: setHere[flag.key] === true, source: "set here" as const };
      }
      const overridden = fromEnv(flag, env);
      if (overridden) {
        return {
          ...base,
          value: overridden.value,
          source: "environment" as const,
          setBy: overridden.name,
        };
      }
      if (flag.key in fromFile) {
        return {
          ...base,
          value: fromFile[flag.key] === true,
          source: "configuration file" as const,
        };
      }
      return { ...base, value: defaults[flag.key] === true, source: "default" as const };
    });
}
