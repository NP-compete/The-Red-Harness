import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { getFileFeatures, getSettings, resetSettings } from "./settings";

function configWith(features: string): string {
  const dir = mkdtempSync(join(tmpdir(), "ui-config-"));
  const path = join(dir, "settings.yaml");
  writeFileSync(path, features);
  return path;
}

beforeEach(() => resetSettings());

afterEach(() => {
  delete process.env.UI_CONFIG_PATH;
  resetSettings();
});

describe("what the configuration file itself declared", () => {
  it("remembers the flags the file set", () => {
    process.env.UI_CONFIG_PATH = configWith("features:\n  memory_enabled: false\n");
    getSettings();
    expect(getFileFeatures()).toEqual({ memory_enabled: false });
  });

  it("is empty when the file mentions no flags", () => {
    process.env.UI_CONFIG_PATH = configWith("branding:\n  title: Test\n");
    getSettings();
    expect(getFileFeatures()).toEqual({});
  });

  it("does not confuse the merged value with what the file said", () => {
    // Defaults carry many flags; only the one in the file is "from
    // the file", and that difference is the whole point.
    process.env.UI_CONFIG_PATH = configWith("features:\n  memory_enabled: false\n");
    const settings = getSettings();
    expect(Object.keys(settings.features).length).toBeGreaterThan(1);
    expect(Object.keys(getFileFeatures())).toEqual(["memory_enabled"]);
  });
});
