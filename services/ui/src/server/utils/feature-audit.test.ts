import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { changesFrom, readFlagChanges, recordFlagChanges } from "./feature-audit";

const redis = vi.hoisted(() => ({ getRedisClient: vi.fn() }));
vi.mock("./redis.js", () => redis);

function store() {
  const list: string[] = [];
  return {
    list,
    lpush: vi.fn(async (_key: string, value: string) => list.unshift(value)),
    ltrim: vi.fn(async () => undefined),
    lrange: vi.fn(async (_key: string, start: number, stop: number) =>
      list.slice(start, stop === -1 ? undefined : stop + 1),
    ),
  };
}

beforeEach(() => redis.getRedisClient.mockReturnValue(store()));
afterEach(() => vi.clearAllMocks());

describe("changesFrom", () => {
  it("reports a flag that was turned off", () => {
    expect(changesFrom({ memory_enabled: true }, { memory_enabled: false })).toEqual([
      { key: "memory_enabled", from: true, to: false },
    ]);
  });

  it("says nothing about a flag written with the value it already had", () => {
    expect(changesFrom({ memory_enabled: true }, { memory_enabled: true })).toEqual([]);
  });

  it("says nothing about a flag nobody touched", () => {
    expect(changesFrom({ memory_enabled: true, auth_enabled: false }, {})).toEqual([]);
  });

  it("reports a flag that had no previous value as newly set", () => {
    expect(changesFrom({}, { memory_enabled: true })).toEqual([
      { key: "memory_enabled", from: null, to: true },
    ]);
  });

  it("reports every flag in one write", () => {
    const found = changesFrom(
      { a: true, b: true },
      { a: false, b: false },
    ).map((c) => c.key);
    expect(found).toEqual(["a", "b"]);
  });
});

describe("recordFlagChanges", () => {
  it("keeps who made the change", async () => {
    const redisStore = store();
    redis.getRedisClient.mockReturnValue(redisStore);
    await recordFlagChanges("sam", [{ key: "memory_enabled", from: true, to: false }]);
    expect(JSON.parse(redisStore.list[0]).who).toBe("sam");
  });

  it("keeps what changed, and both values", async () => {
    const redisStore = store();
    redis.getRedisClient.mockReturnValue(redisStore);
    await recordFlagChanges("sam", [{ key: "memory_enabled", from: true, to: false }]);
    const entry = JSON.parse(redisStore.list[0]);
    expect([entry.key, entry.from, entry.to]).toEqual(["memory_enabled", true, false]);
  });

  it("keeps when", async () => {
    const redisStore = store();
    redis.getRedisClient.mockReturnValue(redisStore);
    await recordFlagChanges("sam", [{ key: "memory_enabled", from: true, to: false }]);
    expect(Date.parse(JSON.parse(redisStore.list[0]).when)).not.toBeNaN();
  });

  it("records a caller it could not name rather than dropping the change", async () => {
    const redisStore = store();
    redis.getRedisClient.mockReturnValue(redisStore);
    await recordFlagChanges("", [{ key: "memory_enabled", from: true, to: false }]);
    expect(JSON.parse(redisStore.list[0]).who).toBeTruthy();
  });

  it("writes one entry per flag", async () => {
    const redisStore = store();
    redis.getRedisClient.mockReturnValue(redisStore);
    await recordFlagChanges("sam", [
      { key: "a", from: true, to: false },
      { key: "b", from: false, to: true },
    ]);
    expect(redisStore.list.length).toBe(2);
  });

  it("does not grow without bound", async () => {
    const redisStore = store();
    redis.getRedisClient.mockReturnValue(redisStore);
    await recordFlagChanges("sam", [{ key: "a", from: true, to: false }]);
    expect(redisStore.ltrim).toHaveBeenCalled();
  });

  it("does not fail a change it could not record", async () => {
    redis.getRedisClient.mockReturnValue(null);
    await expect(
      recordFlagChanges("sam", [{ key: "a", from: true, to: false }]),
    ).resolves.toBeUndefined();
  });
});

describe("readFlagChanges", () => {
  it("reports what was recorded", async () => {
    const redisStore = store();
    redis.getRedisClient.mockReturnValue(redisStore);
    await recordFlagChanges("sam", [{ key: "a", from: true, to: false }]);
    const found = await readFlagChanges();
    expect(found[0].key).toBe("a");
  });

  it("reports the newest first", async () => {
    const redisStore = store();
    redis.getRedisClient.mockReturnValue(redisStore);
    await recordFlagChanges("sam", [{ key: "older", from: true, to: false }]);
    await recordFlagChanges("sam", [{ key: "newer", from: true, to: false }]);
    expect((await readFlagChanges()).map((c) => c.key)).toEqual(["newer", "older"]);
  });

  it("reports nothing rather than failing where there is no store", async () => {
    redis.getRedisClient.mockReturnValue(null);
    expect(await readFlagChanges()).toEqual([]);
  });

  it("skips an entry it cannot read rather than losing the rest", async () => {
    const redisStore = store();
    redisStore.list.push("not json");
    redis.getRedisClient.mockReturnValue(redisStore);
    await recordFlagChanges("sam", [{ key: "a", from: true, to: false }]);
    expect((await readFlagChanges()).map((c) => c.key)).toEqual(["a"]);
  });
});
