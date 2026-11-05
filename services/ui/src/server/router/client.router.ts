import * as crypto from "node:crypto";
import { buildManifest } from "./manifest.js";
import * as fsSync from "node:fs";
import * as fs from "node:fs/promises";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import authCheckPlugin from "../plugins/auth-check.plugin.js";
import { getAgentName, getSettings, resolveAgentHost } from "../utils/settings.js";
import { readOverrides } from "../utils/feature-overrides.js";
import { toClientUserData } from "../utils/session-identity.js";
import {
  buildSandboxCspHeader,
  parseCspQueryParam,
  SANDBOX_JS_CSP,
} from "../utils/mcp-apps-csp.js";

const basePath = (process.env.BASE_PATH || "").replace(/\/+$/, "");
const __dirname = path.dirname(fileURLToPath(import.meta.url));

interface ViteManifestEntry {
  file: string;
  css?: string[];
  imports?: string[];
  isEntry?: boolean;
}

interface ClientAssets {
  /** Entry module, loaded as `type="module"`. */
  script: string;
  /** Stylesheets emitted for the entry. */
  styles: string[];
  /** Static imports of the entry, worth `modulepreload`-ing. */
  preloads: string[];
}

/**
 * Resolve the hashed bundle filenames Vite produced.
 *
 * Filenames carry a content hash, so they are their own cache key and the
 * assets can be served `immutable` with no query string. Read once at
 * startup: the manifest only changes when a new image is built.
 */
function readClientAssets(): ClientAssets {
  const dir = path.join(process.cwd(), "dist/frontend");
  try {
    const manifest = JSON.parse(
      fsSync.readFileSync(path.join(dir, ".vite/manifest.json"), "utf-8"),
    ) as Record<string, ViteManifestEntry>;

    const entry = Object.values(manifest).find((e) => e.isEntry);
    if (!entry) throw new Error("no entry chunk in manifest");

    const preloads = (entry.imports ?? [])
      .map((key) => manifest[key]?.file)
      .filter((f): f is string => Boolean(f));

    return { script: entry.file, styles: entry.css ?? [], preloads };
  } catch (err) {
    // A missing manifest means the client was never built. Fail loudly here
    // rather than serving an HTML shell that silently loads nothing.
    throw new Error(
      `Unable to read dist/frontend/.vite/manifest.json — run \`npm run build:client\`. (${(err as Error).message})`,
    );
  }
}

let cachedAssets: ClientAssets | undefined;
function clientAssets(): ClientAssets {
  cachedAssets ??= readClientAssets();
  return cachedAssets;
}

function substitute(template: string, tokens: Record<string, string>): string {
  return String(template ?? "").replace(/\{(\w+)\}/g, (match, key: string) =>
    key in tokens ? tokens[key] : match,
  );
}

/**
 * Above-the-fold markup for the landing route, rendered into `#root`.
 *
 * Without it nothing is painted until ~250 KB of JS has downloaded, parsed
 * and run, which is what pinned First Contentful Paint at several seconds
 * however small the bundle got: the document itself had no content. The
 * greeting, subtitle and quick prompts are all config, so the server can
 * emit the real copy rather than a grey skeleton, and React replaces the
 * whole subtree on mount.
 *
 * Styling is inline `style` attributes, deliberately. The main stylesheet
 * now loads asynchronously (see the `media="print"` swap), so it can land
 * at any moment — and inline styles outrank anything it brings with it,
 * which keeps the shell from being restyled mid-paint.
 *
 * This duplicates HomePage's layout, so the two can drift. The failure mode
 * is cosmetic — a small jump when React takes over — and it is worth it for
 * a first paint that does not wait on the bundle.
 */
function renderBootShell(opts: {
  agentName: string;
  userName: string;
  content: { greeting: string; greeting_anonymous: string; subtitle: string;
             quick_prompts_heading: string; input_placeholder: string };
  quickPrompts: string[];
  logoUrl?: string;
  title: string;
}): string {
  const t = { agent: opts.agentName, user: opts.userName };
  const text = (s: string) => escapeHtml(substitute(s, t));
  const greeting = text(opts.userName ? opts.content.greeting : opts.content.greeting_anonymous);
  const prompts = opts.quickPrompts.slice(0, 4).map(text);

  const tile =
    "border:1px solid var(--boot-border);border-radius:.75rem;padding:.75rem 1rem;" +
    "font-size:.875rem;text-align:left;color:var(--boot-fg);background:var(--boot-panel)";

  return `<div id="boot-shell" aria-hidden="true" style="position:fixed;inset:0;display:flex;flex-direction:column;background:var(--boot-bg);color:var(--boot-fg);font-family:'Red Hat Text',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <div style="flex:0 0 auto;height:62px;display:flex;align-items:center;gap:.5rem;padding:0 1.5rem;border-bottom:1px solid var(--boot-border)">
    ${opts.logoUrl ? `<img src="${escapeHtml(opts.logoUrl)}" alt="" width="20" height="20" style="height:1.25rem;width:auto">` : ""}
    <span style="font-size:1rem;font-weight:600">${escapeHtml(opts.title)}</span>
  </div>
  <div style="flex:1 1 auto;display:flex;min-height:0">
    <div class="boot-sidebar" style="flex:0 0 278px;border-right:1px solid var(--boot-border)"></div>
    <div style="flex:1 1 auto;display:flex;align-items:center;justify-content:center;padding:2.5rem 1.5rem">
      <div style="max-width:42rem;width:100%;text-align:center">
        <h1 style="font-size:clamp(1.75rem,3.5vw,2.25rem);font-weight:700;margin:0 0 .75rem">${greeting}</h1>
        <p style="font-size:1rem;color:var(--boot-muted);margin:0 0 2rem">${text(opts.content.subtitle)}</p>
        ${prompts.length ? `<h2 style="font-size:.875rem;font-weight:600;color:var(--boot-muted);margin:0 0 .75rem">${text(opts.content.quick_prompts_heading)}</h2>
        <div class="boot-prompts" style="display:grid;grid-template-columns:1fr 1fr;gap:.625rem;margin:0 0 1.5rem">
          ${prompts.map((p) => `<div style="${tile}">${p}</div>`).join("\n          ")}
        </div>` : ""}
        <div style="border:1px solid var(--boot-accent);border-radius:9999px;padding:.875rem 1.25rem;text-align:left;color:var(--boot-muted);font-size:.875rem">${text(opts.content.input_placeholder)}</div>
      </div>
    </div>
  </div>
</div>`;
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function headerValue(request: FastifyRequest, name: string): string | undefined {
  const v = request.headers[name];
  return Array.isArray(v) ? v[0] : v;
}

async function readSandboxAsset(filename: string): Promise<string> {
  const candidates = [
    path.join(__dirname, "../static", filename),
    path.join(process.cwd(), "src/server/static", filename),
    path.join(process.cwd(), "dist/server/static", filename),
  ];
  for (const candidate of candidates) {
    try {
      return await fs.readFile(candidate, "utf-8");
    } catch {
      // try next
    }
  }
  throw new Error(`MCP Apps sandbox asset not found: ${filename}`);
}

function sandboxPathOnly(url: string): string {
  return url.split("?")[0] ?? url;
}

async function routes(fastify: FastifyInstance) {
  await fastify.register(authCheckPlugin);

  await fastify.register(import("@fastify/static"), {
    root: path.join(process.cwd(), "dist/frontend"),
    prefix: "/dist/frontend",
    decorateReply: false,
    // Safe because every reference carries `?v=<content hash>`; a new build
    // produces a new URL rather than relying on revalidation.
    cacheControl: true,
    maxAge: "1y",
    immutable: true,
    // Serve the `.br`/`.gz` siblings written at build time (brotli q11)
    // instead of compressing each response on the fly at q4.
    preCompressed: true,
  });

  await fastify.register(import("@fastify/url-data"));

  // Override global helmet CSP for sandbox assets. Helmet also sets CSP; browsers
  // enforce every Content-Security-Policy header (intersection), so a leftover
  // helmet `base-uri 'self'` would block allowlisted baseUriDomains.
  fastify.addHook("onSend", async (request, reply, payload) => {
    const pathOnly = sandboxPathOnly(request.url);
    if (pathOnly === "/sandbox_proxy.js") {
      reply.header("Content-Security-Policy", SANDBOX_JS_CSP);
      return payload;
    }
    if (pathOnly === "/sandbox_proxy.html") {
      reply.header("X-Frame-Options", "SAMEORIGIN");
      const cspParam = (request.query as { csp?: string }).csp;
      reply.header(
        "Content-Security-Policy",
        buildSandboxCspHeader(parseCspQueryParam(cspParam)),
      );
      return payload;
    }
    return payload;
  });

  fastify.get("/_health", (_request: FastifyRequest, reply: FastifyReply) => {
    reply.send("OK");
  });

  // Without this the `/*` catch-all answers with the SPA shell, which crawlers
  // read as a malformed robots.txt. Set ROBOTS_DISALLOW_ALL=true on a
  // deployment that should stay out of search results.
  const robotsBody =
    process.env.ROBOTS_DISALLOW_ALL === "true"
      ? "User-agent: *\nDisallow: /\n"
      : "User-agent: *\nAllow: /\n";
  fastify.get("/robots.txt", (_request: FastifyRequest, reply: FastifyReply) => {
    return reply.type("text/plain; charset=utf-8").send(robotsBody);
  });

  // https://llmstxt.org/ — a markdown summary of the app for LLM agents.
  // Without the route the `/*` catch-all answers with the SPA shell, which
  // has no H1 and no links, so the file reads as malformed.
  fastify.get("/llms.txt", async (_request: FastifyRequest, reply: FastifyReply) => {
    const cfg = getSettings();
    const agentName = await getAgentName();
    const title = cfg.branding?.title || agentName;
    const summary =
      cfg.branding?.description ||
      `${agentName} — an AI assistant for exploring your data and getting work done.`;
    const base = basePath || "";

    return reply.type("text/plain; charset=utf-8").send(
      `# ${title}

> ${summary}

${title} is a conversational agent. Conversations are called threads and can be
grouped into projects; the agent answers through tools and MCP servers
configured by the deployment.

## Pages

- [Chat](${base}/chat): start a conversation, or pick up an existing thread.
- [Settings](${base}/settings): per-user preferences — theme, model, memory and usage.

## API

- [Agent health](${base}/api/health/agent): liveness of the agent this UI talks to.
- [Branding](${base}/api/config/branding): name, logo and colours for this deployment.
- [Content](${base}/api/config/content): the configurable copy shown on the landing page.
`,
    );
  });


/**
 * `mcp_apps_enabled` as it stands right now, override included.
 *
 * The flag is runtime-overridable, and the admin surface reads the
 * override while these two routes read only the static config. Turn
 * MCP Apps on at runtime and the UI believed it while the sandbox
 * kept answering 404.
 */
async function mcpAppsEnabled(): Promise<boolean> {
  const cfg = getSettings();
  const overrides = await readOverrides();
  return overrides.mcp_apps_enabled ?? cfg.features.mcp_apps_enabled;
}

  /**
   * How the installed application describes itself.
   *
   * Generated rather than served from disk: a committed manifest is
   * a second place the product name lives, and renaming a
   * deployment would change the window title while the dock icon
   * kept the old one until the next image build.
   */
  /**
   * The shell worker, at the root.
   *
   * Served from here rather than from the asset directory because a
   * worker's scope is the path it is served from: one under
   * `/dist/frontend/` could not see a navigation to `/chat`. The
   * filename carries no hash for the same reason the path is fixed
   * — the browser looks for exactly the URL it registered.
   */
  fastify.get("/sw.js", async (_request, reply) => {
    const file = path.join(process.cwd(), "dist/frontend", "sw.js");
    if (!fsSync.existsSync(file)) {
      // No worker in this build. A 404 is correct: registration
      // fails quietly and the application works as it always did.
      return reply.code(404).send("No service worker in this build");
    }
    reply.header("Content-Type", "application/javascript; charset=utf-8");
    // Never cached. A stale worker keeps serving a stale shell, and
    // it is the one file that can outlive its own replacement.
    reply.header("Cache-Control", "no-cache");
    // Scope is the whole application, not the directory this is in.
    reply.header("Service-Worker-Allowed", "/");
    return fsSync.createReadStream(file);
  });

  fastify.get("/manifest.webmanifest", async (_request, reply) => {
    reply.header("Content-Type", "application/manifest+json");
    // Short, not immutable: the name follows configuration, and a
    // long cache would outlive a rename.
    reply.header("Cache-Control", "public, max-age=300");
    return buildManifest();
  });

  fastify.get("/sandbox_proxy.html", async (request, reply) => {
    if (!(await mcpAppsEnabled())) {
      return reply.code(404).send("MCP Apps sandbox is disabled");
    }
    const cspParam = (request.query as { csp?: string }).csp;
    const cspConfig = parseCspQueryParam(cspParam);
    const html = await readSandboxAsset("sandbox_proxy.html");
    return reply
      .type("text/html; charset=utf-8")
      .header("Cache-Control", "no-store")
      .header("X-Content-Type-Options", "nosniff")
      .header("Content-Security-Policy", buildSandboxCspHeader(cspConfig))
      .send(html);
  });

  fastify.get("/sandbox_proxy.js", async (_request, reply) => {
    if (!(await mcpAppsEnabled())) {
      return reply.code(404).send("MCP Apps sandbox is disabled");
    }
    const js = await readSandboxAsset("sandbox_proxy.js");
    return reply
      .type("application/javascript; charset=utf-8")
      .header("Cache-Control", "no-store")
      .header("X-Content-Type-Options", "nosniff")
      .send(js);
  });

  fastify.get("/auth/login", async (request: FastifyRequest, reply: FastifyReply) => {
    const redirect =
      typeof (request.query as { redirect?: string }).redirect === "string"
        ? (request.query as { redirect: string }).redirect
        : "/";
    request.session.redirectUri = redirect;
    return reply.redirect("/login");
  })

  fastify.get("/mcp/oauth/callback", async (request: FastifyRequest, reply: FastifyReply) => {
    const agentHost = resolveAgentHost();
    const qs = request.url.split("?")[1] || "";
    const agentUrl = `${agentHost}/mcp/oauth/callback${qs ? `?${qs}` : ""}`;
    const resp = await fetch(agentUrl, {
      headers: { cookie: request.headers.cookie || "" },
    });
    reply
      .status(resp.status)
      .type(resp.headers.get("content-type") || "text/html");
    return reply.send(await resp.text());
  });

  fastify.get("/*", async (request: FastifyRequest, reply: FastifyReply) => {
    // A client route never has a file extension, so anything that does is a
    // request for a file this server does not have. Answering those with the
    // SPA shell is what made `/robots.txt` look like a malformed robots file
    // and `/.well-known/ai-catalog.json` like malformed JSON — a crawler or
    // agent probing for a well-known file got 200 OK and a page of HTML. 404
    // is the honest answer.
    const requestPath = request.url.split("?")[0];
    if (/\.[a-z0-9]+$/i.test(requestPath)) {
      return reply.code(404).type("text/plain; charset=utf-8").send("Not Found");
    }

    const session = request.session;
    const userData = toClientUserData(session);
    const sessionToken =
      userData.accessToken ||
      headerValue(request, "x-auth-access-token") ||
      headerValue(request, "x-token");
    userData.accessToken = sessionToken || "";

    const agentName = await getAgentName();
    const cfg = getSettings();
    const appData = {
      apiUrl: basePath ? `${basePath}/api/proxy/agent` : "",
      basePath: basePath || "/",
      refreshableToken: "",
      agentName,
      branding: cfg.branding,
      features: cfg.features,
      quickPrompts: cfg.quick_prompts,
      userRole: (session as { role?: string | null }).role ?? null,
    };

    const assetBase = `${basePath || ""}/dist/frontend`;
    const assets = clientAssets();
    const scriptUrl = `${assetBase}/${assets.script}`;
    // Non-render-blocking. The boot shell below is styled entirely with
    // inline `style` attributes, so first paint needs nothing from this
    // file; leaving it blocking meant ~100 KB stood between the user and
    // any content at all. `preload` keeps it at high fetch priority,
    // `media="print"` keeps it out of the critical path, and boot-css.js
    // flips it to `all` the moment the document has parsed. (The flip is an
    // external script because the CSP here is `script-src 'self'`, so the
    // conventional inline `onload` handler would never run.)
    const styleTags = assets.styles
      .flatMap((href) => {
        const url = `${assetBase}/${href}`;
        return [
          `<link rel="preload" as="style" href="${url}">`,
          `<link rel="stylesheet" href="${url}" media="print" data-main-css>`,
          `<noscript><link rel="stylesheet" href="${url}"></noscript>`,
        ];
      })
      .join("\n    ") + `\n    <script src="${assetBase}/boot-css.js" defer></script>`;

    // Written by useThemeSync; absent on a first-ever visit, where the app's
    // own default (dark) is the right guess.
    const bootTheme = (request.cookies as Record<string, string> | undefined)?.ui_theme === "light"
      ? "light"
      : "dark";

    const path0 = request.url.split("?")[0].replace(/\/+$/, "") || "/";
    const landing = path0 === "/" || path0 === "/chat" || path0 === `${basePath}/chat`;
    const bootShell = landing
      ? renderBootShell({
          agentName,
          userName: String(userData.displayName || userData.given_name || ""),
          content: cfg.content,
          quickPrompts: cfg.quick_prompts?.length ? cfg.quick_prompts : cfg.content.quick_prompts,
          logoUrl: cfg.branding?.logo_url,
          title: cfg.branding?.title || agentName,
        })
      : "";
    // Only the entry's static imports are preloaded, and only after the
    // stylesheet tag. The entry itself is NOT preloaded: the boot shell
    // paints as soon as the stylesheet lands, so anything that competes
    // with the stylesheet for bandwidth pushes first paint out. The module
    // script at the end of <body> fetches the entry soon enough.
    const preloadTags = assets.preloads
      .map((f) => `<link rel="modulepreload" href="${assetBase}/${f}">`)
      .join("\n    ");

    reply.type("text/html");
    reply.header("Cache-Control", "no-store");
    return reply.send(`<!DOCTYPE html>
<html lang="en"${bootTheme === "light" ? ' class="boot-light"' : ""}>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" id="favicon" href="${escapeHtml(cfg.branding?.favicon_url || cfg.branding?.logo_url || "/favicon.ico")}" />
    <title>${escapeHtml(agentName)}</title>
    <meta name="description" content="${escapeHtml(cfg.branding?.description || `${agentName} — an AI assistant for exploring your data and getting work done.`)}">
    ${styleTags}
    ${preloadTags}
    <style>
    /* Boot-shell palette. Only these few values are needed before the real
       stylesheet arrives; everything else on the shell is an inline style. */
    html{background:${escapeHtml(cfg.branding.colors.dark.background)}}
    html.boot-light{background:${escapeHtml(cfg.branding.colors.light.background)}}
    :root{--boot-bg:${escapeHtml(cfg.branding.colors.dark.background)};--boot-fg:${escapeHtml(cfg.branding.colors.dark.foreground)};--boot-muted:#9ca7b4;--boot-border:#243041;--boot-panel:#121c2b;--boot-accent:${escapeHtml(cfg.branding.colors.dark.primary)}}
    html.boot-light{--boot-bg:${escapeHtml(cfg.branding.colors.light.background)};--boot-fg:${escapeHtml(cfg.branding.colors.light.foreground)};--boot-muted:#6a6e73;--boot-border:#d2d2d2;--boot-panel:#f7f7f7;--boot-accent:${escapeHtml(cfg.branding.colors.light.primary)}}
    @media (max-width:1023px){#boot-shell .boot-sidebar{display:none}}
    @media (max-width:639px){#boot-shell .boot-prompts{grid-template-columns:1fr}}
    /* PF6/Tailwind v4 co-existence: inline to bypass Vite CSS purging */
    .pf-v6-c-button{--pf-v6-c-button--AlignItems:center}
    .pf-v6-c-button__text{display:inline-flex!important;align-items:center;gap:.375rem}
    .pf-v6-c-button.pf-m-block{--pf-v6-c-button--Display:flex;width:100%}
    .pf-v6-c-masthead.pf-v6-c-masthead{display:flex!important;align-items:center;gap:0}
    .pf-v6-c-masthead__toggle,.pf-v6-c-masthead__main{display:flex;align-items:center}
    .pf-v6-c-masthead__content{flex:1 1 auto;display:flex;align-items:center;justify-content:flex-end}
    .pf-v6-c-page{height:100vh;height:100dvh;max-height:100vh;max-height:100dvh;overflow:hidden}
    .pf-v6-c-page__main-container{align-self:stretch!important;display:flex;flex-direction:column;overflow:hidden}
    .pf-v6-c-page__main{flex:1 1 0%;min-height:0;display:flex;flex-direction:column;overflow:hidden}
    </style>
</head>
<body>
    <div id="root" data-user="${encodeURIComponent(JSON.stringify(userData || {}))}" data-app="${encodeURIComponent(JSON.stringify(appData))}">${bootShell}</div>
    <script type="module" src="${scriptUrl}"></script>
</body>
</html>`);
  });
}

export { routes as clientRoutes };
