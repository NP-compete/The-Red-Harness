import { describe, it, expect } from "vitest";

import { getSettings } from "./utils/settings.js";

/**
 * The directives a service worker and a manifest need.
 *
 * Derived from configuration like every other directive rather than
 * appended by hand at the point of use — a directive added in one
 * place and not the other is how a policy becomes two policies.
 */
describe("the content security policy", () => {
  const csp = () => getSettings().security.helmet.csp;

  it("allows a worker from this origin", () => {
    expect(csp().worker_src).toEqual(["'self'"]);
  });

  it("allows a manifest from this origin", () => {
    expect(csp().manifest_src).toEqual(["'self'"]);
  });

  it("allows a worker from nowhere else", () => {
    // A worker intercepts every request in scope. One loaded from
    // somewhere else would see all of them.
    expect(csp().worker_src).not.toContain("*");
  });
});
