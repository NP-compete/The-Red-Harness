import { describe, expect, it } from "vitest";

import { REGISTRY, describeFeatures } from "./feature-registry";

const defaults = { auth_enabled: false, memory_enabled: true, mcp_dcr_enabled: true };

/** Runs `body` with one declared-but-hidden flag in the registry. */
function withHiddenFlag<T>(body: () => T): T {
  REGISTRY.kept_quiet = {
    key: "kept_quiet",
    scope: "deployment",
    effect: "Something an operator has no business switching.",
    env: ["FEATURE_KEPT_QUIET"],
    uiExposed: false,
  };
  try {
    return body();
  } finally {
    delete REGISTRY.kept_quiet;
  }
}

describe("describeFeatures", () => {
  it("reports a flag nobody has touched as coming from its default", () => {
    const [auth] = describeFeatures(defaults, {}, {}).filter((f) => f.key === "auth_enabled");
    expect(auth.value).toBe(false);
    expect(auth.source).toBe("default");
  });

  it("reports a flag the configuration file set", () => {
    const [auth] = describeFeatures(defaults, { auth_enabled: true }, {}).filter(
      (f) => f.key === "auth_enabled",
    );
    expect(auth.value).toBe(true);
    expect(auth.source).toBe("configuration file");
  });

  it("reports a flag the environment set", () => {
    const [auth] = describeFeatures(defaults, {}, { AUTH_ENABLED: "true" }).filter(
      (f) => f.key === "auth_enabled",
    );
    expect(auth.value).toBe(true);
    expect(auth.source).toBe("environment");
  });

  it("lets the environment win over the file, and says so", () => {
    const [auth] = describeFeatures(
      defaults,
      { auth_enabled: true },
      { AUTH_ENABLED: "false" },
    ).filter((f) => f.key === "auth_enabled");
    expect(auth.value).toBe(false);
    expect(auth.source).toBe("environment");
  });

  it("names the environment variable that decided it", () => {
    const [auth] = describeFeatures(defaults, {}, { AUTH_ENABLED: "true" }).filter(
      (f) => f.key === "auth_enabled",
    );
    expect(auth.setBy).toBe("AUTH_ENABLED");
  });

  it("prefers the current name over the one kept for compatibility", () => {
    const [auth] = describeFeatures(
      defaults,
      {},
      { AUTH_ENABLED: "false", FEATURE_AUTH_ENABLED: "true" },
    ).filter((f) => f.key === "auth_enabled");
    expect(auth.value).toBe(true);
    expect(auth.setBy).toBe("FEATURE_AUTH_ENABLED");
  });

  it("says what each flag changes, so an operator can weigh it", () => {
    for (const described of describeFeatures(defaults, {}, {})) {
      expect(described.effect.length).toBeGreaterThan(10);
    }
  });

  it("says which level of the stack a flag belongs to", () => {
    const scopes = describeFeatures(defaults, {}, {}).map((f) => f.scope);
    expect(scopes.every((s) => s === "deployment" || s === "agent" || s === "user")).toBe(
      true,
    );
  });

  it("leaves out a flag that is not meant to be shown", () => {
    // Written against a flag put there for the purpose. Filtering
    // the registry for hidden flags matched nothing, so the loop
    // body never ran and the test passed whether or not
    // `describeFeatures` honoured `uiExposed` at all.
    const shown = withHiddenFlag(() =>
      describeFeatures({ ...defaults, kept_quiet: true }, {}, {}).map((f) => f.key),
    );
    expect(shown).not.toContain("kept_quiet");
  });

  it("shows the other flags while one is hidden", () => {
    const shown = withHiddenFlag(() => describeFeatures(defaults, {}, {}).map((f) => f.key));
    expect(shown).toContain("auth_enabled");
  });

  it("will not report a hidden flag even when set here", () => {
    // The override path merges over everything else, so a flag
    // hidden from the page must not reappear through it.
    const shown = withHiddenFlag(() =>
      describeFeatures(defaults, {}, {}, { kept_quiet: true }, ["kept_quiet"]).map(
        (f) => f.key,
      ),
    );
    expect(shown).not.toContain("kept_quiet");
  });

  it("will not report a hidden flag the environment set", () => {
    const shown = withHiddenFlag(() =>
      describeFeatures(defaults, {}, { FEATURE_KEPT_QUIET: "true" }).map((f) => f.key),
    );
    expect(shown).not.toContain("kept_quiet");
  });

  it("says nothing about a value with no flag declared for it", () => {
    const shown = describeFeatures({ ...defaults, invented: true }, {}, {}).map(
      (f) => f.key,
    );
    expect(shown).not.toContain("invented");
  });

  it("reports a declared flag even when the settings never mention it", () => {
    const shown = describeFeatures({}, {}, {}).map((f) => f.key);
    expect(shown).toContain("auth_enabled");
  });

  it("puts them in a settled order rather than whatever the object gave", () => {
    const keys = describeFeatures(defaults, {}, {}).map((f) => f.key);
    expect(keys).toEqual([...keys].sort());
  });
});

describe("REGISTRY", () => {
  it("declares every flag the settings carry", () => {
    // A flag read somewhere and declared nowhere is the one that ends
    // up with two different defaults in two different places.
    const declared = Object.keys(REGISTRY);
    for (const key of ["auth_enabled", "memory_enabled", "mcp_dcr_enabled"]) {
      expect(declared).toContain(key);
    }
  });

  it("gives each flag its own key", () => {
    for (const [key, flag] of Object.entries(REGISTRY)) expect(flag.key).toBe(key);
  });
});

describe("a flag an operator has set here", () => {
  it("takes the value the operator chose", () => {
    const [auth] = describeFeatures(defaults, {}, {}, { auth_enabled: true }).filter(
      (f) => f.key === "auth_enabled",
    );
    expect(auth.value).toBe(true);
  });

  it("says an operator set it, not the file", () => {
    const [m] = describeFeatures(
      defaults,
      { memory_enabled: false },
      {},
      { memory_enabled: true },
    ).filter((f) => f.key === "memory_enabled");
    expect(m.source).toBe("set here");
  });

  it("wins over the environment, because that is what the agent does", () => {
    const [auth] = describeFeatures(
      defaults,
      {},
      { AUTH_ENABLED: "false" },
      { auth_enabled: true },
    ).filter((f) => f.key === "auth_enabled");
    expect(auth.value).toBe(true);
    expect(auth.source).toBe("set here");
  });

  it("says which flags can be set here at all", () => {
    const described = describeFeatures(defaults, {}, {}, {}, ["memory_enabled"]);
    const byKey = Object.fromEntries(described.map((f) => [f.key, f]));
    expect(byKey.memory_enabled.overridable).toBe(true);
    expect(byKey.auth_enabled.overridable).toBe(false);
  });

  it("treats nothing as overridable until told otherwise", () => {
    expect(describeFeatures(defaults, {}, {}, {}).every((f) => !f.overridable)).toBe(true);
  });
});

describe("the switches an operator may actually throw", () => {
  it("every overridable flag is one the registry declares", async () => {
    // Otherwise it is writable by API and absent from the page, so
    // nothing on screen says it was changed or what it does.
    const { OVERRIDABLE } = await import("./feature-overrides");
    for (const key of OVERRIDABLE) expect(Object.keys(REGISTRY)).toContain(key);
  });

  it("every overridable flag is one an operator may see", async () => {
    // A flag hidden from the page but writable through the endpoint
    // is the exact thing `uiExposed` exists to prevent.
    const { OVERRIDABLE } = await import("./feature-overrides");
    for (const key of OVERRIDABLE) expect(REGISTRY[key].uiExposed).toBe(true);
  });

  it("a hidden flag is not offered as overridable", async () => {
    const { OVERRIDABLE } = await import("./feature-overrides");
    withHiddenFlag(() => {
      expect(OVERRIDABLE as readonly string[]).not.toContain("kept_quiet");
    });
  });
});
