#!/usr/bin/env node
/**
 * `harness-ui` — serve the interface, or find out why it will not.
 *
 * The npm scripts already cover building and developing, and this
 * does not replace them. What was missing is the other half of
 * operating a service: a `doctor` that names what is absent
 * before the process exits on it, and a `serve` that does not
 * require knowing which directory to stand in.
 *
 * Exit codes match `harness`: 0 worked, 1 did
 * not, 2 used wrongly, 5 worked but something is missing.
 */
import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const USAGE_ERROR = 2;
const DEGRADED = 5;

const BUILT = join(ROOT, "dist", "server", "index.js");

function doctor(json) {
  const findings = [];

  if (!existsSync(BUILT)) {
    findings.push(`not built: ${BUILT} is absent — run \`npm run build\``);
  }
  const sign = process.env.COOKIE_SIGN ?? "";
  if (!sign) {
    findings.push("COOKIE_SIGN is not set; the server refuses to start without it");
  } else if (sign.length < 32) {
    findings.push(`COOKIE_SIGN is ${sign.length} chars; the server requires 32`);
  }
  if (!process.env.AGENT_HOST) {
    findings.push("AGENT_HOST is not set — the BFF will not know where the agent is");
  }
  // A config the settings page cannot read is a blank page rather
  // than an error, which is the slowest kind to diagnose.
  const config = join(ROOT, "..", "..", "config", "agent", "runtime", "ui.yaml");
  if (!existsSync(config)) {
    findings.push(`no ui.yaml at ${config}; defaults will be used`);
  }

  if (json) {
    console.log(JSON.stringify({ ok: findings.length === 0, findings }));
  } else if (findings.length) {
    console.log("the interface is not ready:");
    for (const one of findings) console.log(`  ${one}`);
  } else {
    console.log("Nothing to report. This service looks usable.");
  }
  return findings.length ? DEGRADED : 0;
}

function passthrough(script, rest) {
  // npm from the package root, so the caller does not have to be
  // standing in it.
  const run = spawnSync("npm", ["run", script, ...rest], {
    cwd: ROOT,
    stdio: "inherit",
  });
  return run.status ?? 1;
}

function serve(rest) {
  if (!existsSync(BUILT)) {
    console.error(`${BUILT} is absent. \`harness-ui build\` first, or use \`dev\`.`);
    return 1;
  }
  const run = spawnSync(process.execPath, [BUILT, ...rest], {
    cwd: ROOT,
    stdio: "inherit",
  });
  return run.status ?? 1;
}

function version() {
  const pkg = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));
  console.log(`harness-ui ${pkg.version ?? "0.0.0"}`);
  return 0;
}

const [command, ...rest] = process.argv.slice(2);
const json = rest.includes("--json");

switch (command) {
  case "serve":
    process.exit(serve(rest));
  case "dev":
    process.exit(passthrough("dev", rest));
  case "build":
    process.exit(passthrough("build", rest));
  case "check":
    process.exit(passthrough("lint", rest));
  case "doctor":
    process.exit(doctor(json));
  case "--version":
  case "version":
    process.exit(version());
  default:
    console.log(
      [
        "usage: harness-ui {serve,dev,build,check,doctor,version}",
        "",
        "  serve     the built interface and its BFF",
        "  dev       vite dev server, reloads on save",
        "  build     client and server bundles",
        "  check     lint",
        "  doctor    what is missing, before it fails to start",
        "",
        "exit codes: 0 it worked, 1 it did not, 2 used wrongly,",
        "            5 it worked but something is missing",
      ].join("\n"),
    );
    process.exit(command ? USAGE_ERROR : USAGE_ERROR);
}
