import { describe, it, expect } from "vitest";

import { getSettings } from "./settings.js";

/**
 * What the deployment says about notifications.
 *
 * Every one of these defaults matters more than usual, because the
 * cost of getting them wrong is not a broken page: it is a browser
 * permission prompt shown where delivery does not work, which
 * teaches people to refuse the next one too.
 */
describe("the notification settings a deployment ships with", () => {
  const pwa = () => getSettings().pwa;

  it("are read from the configuration", () => {
    expect(pwa()).toBeDefined();
  });

  it("name the platforms where a notification is worth asking for", () => {
    expect(pwa().notifications.platforms).toEqual(
      expect.arrayContaining(["macOS", "Windows", "Linux"]),
    );
  });

  it("do not include a platform where delivery is unreliable", () => {
    const platforms = pwa().notifications.platforms;
    expect(platforms).not.toContain("iOS");
    expect(platforms).not.toContain("Android");
  });

  it("can be switched off for each kind of event", () => {
    expect(Object.keys(pwa().notifications.events).sort()).toEqual([
      "approval_required",
      "connection_required",
      "run_complete",
      "run_failed",
    ]);
  });

  it("keep conversation content out of a notification by default", () => {
    // It renders on a lock screen.
    expect(pwa().notifications.include_detail).toBe(false);
  });

  it("ship with push off", () => {
    // Push sends a message through a browser vendor's service. That
    // is a decision a deployment makes, not a default it inherits.
    expect(pwa().push.enabled).toBe(false);
  });

  it("carry no push key by default", () => {
    expect(pwa().push.vapid_public_key).toBe("");
  });
});

describe("what the browser is told about notifications", () => {
  it("is served without being cached", async () => {
    // A cached answer outlives the deployment decision that made it.
    const { buildPwaResponse } = await import("../router/pwa.js");
    expect(buildPwaResponse().cacheControl).toBe("no-store");
  });

  it("carries the platform allowlist, so the client can gate itself", async () => {
    const { buildPwaResponse } = await import("../router/pwa.js");
    expect(buildPwaResponse().body.notifications.platforms).toContain("macOS");
  });

  it("carries no push key the deployment has not set", async () => {
    const { buildPwaResponse } = await import("../router/pwa.js");
    expect(buildPwaResponse().body.push.vapid_public_key).toBe("");
  });

  it("never carries a private key", async () => {
    // There is no field for one, and that is the point: a private
    // key reaching the browser is the whole failure.
    const { buildPwaResponse } = await import("../router/pwa.js");
    expect(JSON.stringify(buildPwaResponse().body)).not.toMatch(/private/i);
  });
});
