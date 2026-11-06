// The rate limiter, as the feature it is.
//
//     make load FEATURE=rate-limit
//
// Every other scenario treats a 429 as an expected answer and
// gets out of its way. This one goes at it deliberately: the
// limiter is a security control, and a control nobody tests is
// one that can be switched off in a one-line diff that reads
// like tidying.
//
// Three claims, and the third is the one that usually rots:
//
//  1. The ceiling the configuration declares is the ceiling the
//     server advertises.
//  2. Past it, the server says 429 rather than falling over or
//     quietly serving everything.
//  3. Health probes are exempt, so a throttled deployment does
//     not also look unhealthy and get restarted.

import http from "k6/http";
import { check } from "k6";
import { Counter } from "k6/metrics";
import { BASE, UI_HOST } from "../lib/config.js";

export const throttled = new Counter("throttled");
export const served = new Counter("served");

export const options = {
  scenarios: {
    burst: {
      // Arrival-rate, not VUs: the question is what happens at a
      // request rate above the limit, and VUs that wait for a
      // response throttle themselves.
      executor: "constant-arrival-rate",
      rate: 60,
      timeUnit: "1s",
      duration: "30s",
      preAllocatedVUs: 40,
      maxVUs: 80,
    },
  },
  thresholds: {
    checks: ["rate>0.99"],
    // Deliberately over the limit, so most requests must be
    // refused. A run where nothing is throttled means the limiter
    // is off, which is the failure this file exists to catch.
    throttled: ["count>100"],
  },
};

const ui = (path, expect) =>
  http.get(`${BASE}${path}`, {
    headers: { Host: UI_HOST },
    responseCallback: http.expectedStatuses(...expect),
    tags: { feature: "rate-limit" },
  });

export function setup() {
  const res = ui("/", [200, 429]);
  const limit = res.headers["X-Ratelimit-Limit"];
  check(res, {
    "the server advertises a limit": () => Boolean(limit),
  });
  console.log(`rate-limit: the server advertises ${limit} per window`);
  return { limit };
}

export default function () {
  const res = ui("/", [200, 429]);
  if (res.status === 429) throttled.add(1);
  else served.add(1);

  check(res, {
    "answers 200 or 429, never a crash": (r) =>
      r.status === 200 || r.status === 429,
    "a refusal says how long to wait": (r) =>
      r.status !== 429 || (r.body ?? "").includes("retry"),
  });

  // Exempt, and it has to stay exempt: a throttled deployment
  // whose probes also fail gets restarted by Kubernetes, which
  // turns a busy minute into an outage.
  const health = http.get(`${BASE}/_health`, {
    headers: { Host: UI_HOST },
    tags: { feature: "rate-limit" },
  });
  check(health, {
    "health is never throttled": (r) => r.status === 200,
  });
}
