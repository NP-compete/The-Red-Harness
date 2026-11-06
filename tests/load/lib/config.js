// Where the load lands, and how hard.
//
// Defaults target the Kind ingress, which is the only stack most
// people have. Everything is an environment variable so the same
// scripts run against preprod without editing a file.

const env = (name, fallback) => __ENV[name] ?? fallback;

export const BASE = env("LOAD_BASE_URL", "http://localhost:8081");
export const AGENT_HOST = env("LOAD_AGENT_HOST", "agent.localhost");
export const UI_HOST = env("LOAD_UI_HOST", "ui.localhost");

// The profile the brief asks for: 80 users, all heavy.
export const VUS = Number(env("LOAD_VUS", "80"));
export const DURATION = env("LOAD_DURATION", "5m");
export const RAMP = env("LOAD_RAMP", "1m");

// A heavy user does not sit and read. This is the pause between
// one action and the next, in seconds — short on purpose.
export const THINK_MIN = Number(env("LOAD_THINK_MIN", "0.5"));
export const THINK_MAX = Number(env("LOAD_THINK_MAX", "2"));

// A chat turn costs a model call. At 80 VUs against a real
// provider that is mostly a measurement of somebody's rate
// limiter, and a bill. Off unless asked for; `make load-chat`
// sets it, and the preflight prints which model answered.
export const CHAT = env("LOAD_CHAT", "0") === "1";

// How long one chat turn is allowed to take. Generous: this is a
// language model, and a timeout here would be recorded as a
// harness failure when it is a slow answer.
export const CHAT_TIMEOUT = env("LOAD_CHAT_TIMEOUT", "120s");

// Measured, so nobody repeats it: spoofing `X-Forwarded-For` per
// VU does **not** give each one its own rate-limit bucket here.
// The ingress appends the real peer, and with `trust_proxy: 1`
// the BFF keys on that — one address for the whole generator, as
// `remoteAddress` in its logs confirms. So 80 users from one
// machine are one client to the limiter, and the UI's 600/min is
// a ceiling on the whole run. `features/rate-limit.js` asserts
// that ceiling on purpose; the capacity run counts 429s apart
// from failures rather than pretending they did not happen.

export const headers = (host = AGENT_HOST, user = null) => ({
  "Content-Type": "application/json",
  Host: host,
  // One user id per VU, so per-user rate limits and per-user
  // caches behave as they would with real people. A single
  // shared id would pile every request into one bucket and
  // measure the limiter instead of the system.
  "X-User-Id": user ?? `load-user-${__VU}`,
});

export const thresholds = {
  // A failed check is a wrong answer, not a slow one — these stay
  // tight whatever the latency budget is.
  checks: ["rate>0.99"],
  http_req_failed: ["rate<0.01"],
  // Read paths. The chat path has its own trend and is excluded,
  // because one 20-second model call would otherwise drag the
  // percentile for every list endpoint with it.
  "http_req_duration{kind:read}": ["p(95)<800", "p(99)<2000"],
  "http_req_duration{kind:write}": ["p(95)<1500"],
};
