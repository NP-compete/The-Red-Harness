import { afterEach, describe, expect, it, vi } from "vitest";

import { overridesAvailable } from "./feature-overrides";

const redis = vi.hoisted(() => ({ getRedisClient: vi.fn() }));
vi.mock("./redis.js", () => redis);

afterEach(() => vi.clearAllMocks());

describe("overridesAvailable", () => {
  it("says no when there is nowhere to keep an override", () => {
    redis.getRedisClient.mockReturnValue(null);
    expect(overridesAvailable()).toBe(false);
  });

  it("says yes when there is", () => {
    redis.getRedisClient.mockReturnValue({});
    expect(overridesAvailable()).toBe(true);
  });
});
