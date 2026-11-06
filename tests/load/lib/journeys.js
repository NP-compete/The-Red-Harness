// What a heavy user of each feature actually does.
//
// One exported function per feature, so `features/<name>.js` runs
// it alone and `all-features.js` runs the mix. Every path here was
// taken from `/openapi.json` rather than guessed; a 404 under load
// is a green test measuring a wrong URL.

import { check } from "k6";
import {
  post,
  reads,
  readsOptional,
  uiReads,
  newThread,
  dropThread,
  ask,
  think,
} from "./api.js";
import { CHAT } from "./config.js";

const QUESTIONS = [
  "In one sentence, what are you for?",
  "What can you help me with today?",
  "Summarise what tools you have available.",
  "What is 17 times 23? Just the number.",
];

/** Chat: the one journey that costs a model call. */
export function chat() {
  if (!CHAT) {
    // Still exercise the thread lifecycle, which is the part of
    // chat that is ours rather than the provider's.
    const id = newThread("chat");
    reads(`/threads/${id}/state`, "chat");
    dropThread(id, "chat");
    think();
    return;
  }
  const id = newThread("chat");
  if (!id) return;
  ask(id, QUESTIONS[Math.floor(Math.random() * QUESTIONS.length)]);
  reads(`/threads/${id}/state`, "chat");
  think();
}

/** The sidebar: the single most-requested view in the product. */
export function threads() {
  reads("/threads", "threads");
  post("/threads/search", { limit: 20 }, { feature: "threads" });
  think();
}

export function projects() {
  reads("/projects", "projects");
  think();
}

export function spaces() {
  const res = reads("/spaces", "spaces");
  let first = null;
  try {
    const body = res.json();
    const list = Array.isArray(body) ? body : body.spaces || [];
    first = list.length ? list[0].space_id || list[0].id : null;
  } catch {
    first = null;
  }
  if (first) reads(`/spaces/${first}/messages`, "spaces");
  think();
}

/** Analytics: the heaviest read path, several aggregates per page. */
export function analytics() {
  reads("/analytics/summary", "analytics");
  reads("/analytics/timeseries", "analytics");
  reads("/analytics/models", "analytics");
  think();
}

/** Config: the whole editable tree, which is a large document. */
export function config() {
  reads("/config/tree", "config");
  reads("/config/settings", "config");
  think();
}

export function scheduled() {
  const res = post("/runs/crons/search", { limit: 20 }, { feature: "scheduled" });
  check(res, { "crons searched": (r) => r.status === 200 });
  think();
}

export function catalogue() {
  reads("/skills", "catalogue");
  reads("/subagents", "catalogue");
  reads("/assistants", "catalogue");
  reads("/features", "catalogue");
  think();
}

export function search() {
  reads("/search/threads?q=ingest", "search");
  think();
}

export function knowledge() {
  // Personal knowledge is a capability a deployment turns on; this
  // one has it off, and the route says so with a 404.
  readsOptional("/knowledge/documents", "knowledge");
  reads("/documents", "knowledge");
  think();
}

/** MCP status, which the integrations page polls per server. */
export function mcp() {
  reads("/mcp/servers", "mcp");
  reads("/mcp/oauth/connections", "mcp");
  think();
}

export function personalization() {
  reads("/personalization/preferences", "personalization");
  reads("/personalization/memories", "personalization");
  think();
}

export function evals() {
  reads("/evals/status", "evals");
  reads("/evals/checks", "evals");
  think();
}

/** The SPA itself: the BFF, not the agent. */
export function ui() {
  uiReads("/", "ui");
  uiReads("/api/config/branding", "ui");
  think();
}

/** Every journey, by name, for the mixed run and the Makefile. */
export const JOURNEYS = {
  chat,
  threads,
  projects,
  spaces,
  analytics,
  config,
  scheduled,
  catalogue,
  search,
  knowledge,
  mcp,
  personalization,
  evals,
  ui,
};
