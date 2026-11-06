// One place that knows how to call the agent, so a scenario reads
// as the journey it is rather than as HTTP.

import http from "k6/http";
import { check, sleep } from "k6";
import { Trend, Counter } from "k6/metrics";
import {
  BASE,
  AGENT_HOST,
  UI_HOST,
  headers,
  THINK_MIN,
  THINK_MAX,
  CHAT_TIMEOUT,
} from "./config.js";

export const chatTurn = new Trend("chat_turn_ms", true);
export const chatTurns = new Counter("chat_turns");
export const refusals = new Counter("refusals");
export const notOffered = new Counter("feature_not_offered");
export const limited = new Counter("rate_limited");

/** A pause a person would take, not a fixed beat every VU shares. */
export function think() {
  sleep(THINK_MIN + Math.random() * (THINK_MAX - THINK_MIN));
}

function call(method, path, body, { kind, host, feature, timeout, expect } = {}) {
  const params = {
    headers: headers(host ?? AGENT_HOST),
    tags: { kind: kind ?? "read", feature: feature ?? "misc" },
  };
  if (timeout) params.timeout = timeout;
  // Declared per call rather than loosening the global threshold:
  // a 429 from the limiter and a 404 from a feature that is off
  // are expected answers, and every *other* non-2xx stays a
  // failure that `http_req_failed` must still catch.
  if (expect) params.responseCallback = http.expectedStatuses(...expect);
  const url = `${BASE}${path}`;
  return body === undefined
    ? http.request(method, url, null, params)
    : http.request(method, url, JSON.stringify(body), params);
}

export const get = (path, opts) => call("GET", path, undefined, opts);
export const post = (path, body, opts) =>
  call("POST", path, body ?? {}, { kind: "write", ...opts });
export const del = (path, opts) =>
  call("DELETE", path, undefined, { kind: "write", ...opts });

/** A GET that is only useful if it came back 200 with a body. */
export function reads(path, feature) {
  const res = get(path, { feature });
  check(res, {
    [`${path} is 200`]: (r) => r.status === 200,
    [`${path} returned a body`]: (r) => (r.body ?? "").length > 0,
  });
  return res;
}

/**
 * A GET for a feature a deployment may have switched off.
 *
 * 404 is the answer when the capability is not offered here —
 * `knowledge_routes._offered()` raises exactly that — so counting
 * it as a failure would make the suite red on a correctly
 * configured deployment. Counted, so a run can say how much of
 * the surface it actually reached.
 */
export function readsOptional(path, feature) {
  const res = get(path, { feature, expect: [200, 404] });
  check(res, {
    [`${path} answered`]: (r) => r.status === 200 || r.status === 404,
  });
  if (res.status === 404) notOffered.add(1);
  return res;
}

/**
 * The BFF, which rate-limits per client address.
 *
 * A single-machine run is one client however many VUs it has, so
 * 429 is the limiter working rather than the server failing.
 * Counted on its own metric: a run where most UI calls were
 * throttled has measured the limiter, and the summary should say
 * so instead of reporting a tidy p95 over the few that got in.
 */
export function uiReads(path, feature) {
  const res = get(path, { host: UI_HOST, feature, expect: [200, 429] });
  check(res, {
    [`ui ${path} answered`]: (r) => r.status === 200 || r.status === 429,
  });
  if (res.status === 429) limited.add(1);
  return res;
}

export function newThread(feature, metadata = {}) {
  const res = post("/threads", { metadata }, { feature });
  const ok = check(res, { "thread created": (r) => r.status < 300 });
  if (!ok) return null;
  try {
    return res.json("thread_id");
  } catch {
    return null;
  }
}

/**
 * One chat turn, waited out.
 *
 * Recorded on its own trend rather than the shared duration
 * histogram: a model call is seconds and a list call is
 * milliseconds, and mixing them makes a p95 that describes
 * neither.
 */
export function ask(threadId, question, feature = "chat") {
  const started = Date.now();
  const res = post(
    `/threads/${threadId}/runs/wait`,
    {
      assistant_id: "agent",
      input: { messages: [{ role: "human", content: question }] },
    },
    { feature, kind: "chat", timeout: CHAT_TIMEOUT },
  );
  chatTurn.add(Date.now() - started);
  chatTurns.add(1);

  const ok = check(res, {
    "chat turn answered": (r) => r.status === 200,
    "chat turn has a message": (r) => (r.body ?? "").includes("messages"),
  });
  // A refusal is a real answer and not an error, but a run where
  // every turn is refused is a green test measuring nothing.
  if (ok && (res.body ?? "").includes("unable to respond")) refusals.add(1);
  return res;
}

/** Tidy up only what this VU made. */
export function dropThread(threadId, feature) {
  if (threadId) del(`/threads/${threadId}`, { feature });
}
