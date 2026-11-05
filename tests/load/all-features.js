// Every feature at once, 80 heavy users.
//
//     make load                  the 80-user mix
//     make load VUS=10 DURATION=1m   a smaller sanity pass
//
// The weights are what a working day looks like rather than an
// even split: people read the sidebar constantly, open analytics
// occasionally, and edit config rarely. An even split would spend
// most of the run measuring the page nobody opens.

import { group } from "k6";
import { JOURNEYS } from "./lib/journeys.js";
import { VUS, DURATION, RAMP, CHAT, thresholds, BASE, AGENT_HOST } from "./lib/config.js";
import http from "k6/http";

const MIX = [
  ["threads", 22],
  ["chat", 18],
  ["ui", 14],
  ["catalogue", 10],
  ["analytics", 8],
  ["projects", 7],
  ["spaces", 6],
  ["search", 5],
  ["scheduled", 3],
  ["mcp", 3],
  ["config", 2],
  ["knowledge", 1],
  ["personalization", 1],
];

const TOTAL = MIX.reduce((sum, [, weight]) => sum + weight, 0);

export const options = {
  scenarios: {
    heavy_users: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: RAMP, target: VUS },
        { duration: DURATION, target: VUS },
        { duration: "30s", target: 0 },
      ],
      gracefulRampDown: "30s",
    },
  },
  thresholds,
};

/**
 * Say what was measured, before measuring it.
 *
 * A run against a real provider with chat on is mostly a
 * measurement of somebody's rate limiter, and a run with chat off
 * is not a measurement of chat. Both are useful; being unclear
 * which one happened is not.
 */
export function setup() {
  const res = http.get(`${BASE}/config/settings`, {
    headers: { Host: AGENT_HOST, "X-User-Id": "load-setup" },
  });
  let model = "unknown";
  try {
    for (const field of res.json("fields") || []) {
      if (field.name === "MODEL_OVERRIDE" && field.value) model = field.value;
      if (field.name === "DEFAULT_MODEL" && model === "unknown") model = field.value;
    }
  } catch {
    model = "unreadable";
  }
  console.log(`load: ${VUS} heavy users for ${DURATION} against ${BASE}`);
  console.log(`load: chat turns ${CHAT ? "ON" : "OFF"}, model ${model}`);
  if (CHAT && !String(model).startsWith("mock")) {
    console.warn(
      "load: chat is ON against a real model — this spends money and " +
        "will mostly measure the provider's rate limit. " +
        "Set MODEL_OVERRIDE=mock-model to measure the harness.",
    );
  }
  return { model };
}

function pick() {
  let roll = Math.random() * TOTAL;
  for (const [name, weight] of MIX) {
    roll -= weight;
    if (roll <= 0) return name;
  }
  return MIX[0][0];
}

export default function () {
  const name = pick();
  group(name, () => JOURNEYS[name]());
}
