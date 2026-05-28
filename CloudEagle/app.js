/**
 * CloudEagle Integration Builder — prototype
 * Builds one coherent TypeScript module from selected sections.
 */

const FEATURE_ORDER = [
  ["client", "API client"],
  ["auth", "Auth setup"],
  ["data", "Users & usage"],
  ["errors", "Error handling"],
  ["pagination", "Pagination"],
  ["logging", "Logging"],
];

/** Ordered fragments; assembled without cross-file imports */
const FRAGMENTS = {
  client: `
const CALENDLY_API_BASE = "https://api.calendly.com";

export type CalendlyClientConfig = {
  fetchImpl?: typeof fetch;
  getAccessToken?: () => string | Promise<string>;
  extraHeaders?: Record<string, string>;
};

export function createCalendlyClient(config: CalendlyClientConfig = {}) {
  const fetchFn = config.fetchImpl ?? fetch;

  async function authorizedHeaders(): Promise<HeadersInit> {
    const token = config.getAccessToken ? await config.getAccessToken() : undefined;
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...config.extraHeaders,
    };
    if (token) headers.Authorization = \`Bearer \${token}\`;
    return headers;
  }

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const url = path.startsWith("http") ? path : \`\${CALENDLY_API_BASE}\${path}\`;
    const res = await fetchFn(url, {
      ...init,
      headers: { ...(await authorizedHeaders()), ...(init.headers as object) },
    });
    const text = await res.text();
    if (!res.ok) throw new CalendlyHttpError(res.status, text, res.headers);
    return text ? (JSON.parse(text) as T) : ({} as T);
  }

  return { request };
}`,

  auth: `
/** Swap getAccessToken for OAuth token endpoint + refresh in production */
export function bearerTokenProvider(token: string) {
  return () => token;
}

export function envTokenProvider(envVar = "CALENDLY_ACCESS_TOKEN") {
  return () => {
    const v = typeof process !== "undefined" ? process.env?.[envVar] : undefined;
    if (!v) throw new Error(\`Missing \${envVar}\`);
    return v;
  };
}

export function createCalendlyClientFromEnv() {
  return createCalendlyClient({ getAccessToken: envTokenProvider() });
}`,

  data: `
export type UserResource = {
  uri: string;
  name: string;
  email: string;
  slug?: string;
};

export async function getCurrentUser(client: ReturnType<typeof createCalendlyClient>) {
  return client.request<{ resource: UserResource }>("/users/me");
}

export async function listOrganizationMemberships(
  client: ReturnType<typeof createCalendlyClient>,
  organizationUri: string,
  query?: Record<string, string>
) {
  const q = new URLSearchParams({ organization: organizationUri, ...query }).toString();
  return client.request<{ collection: Array<{ user: UserResource }> }>(
    \`/organization_memberships?\${q}\`
  );
}

/** Usage-shaped signal: scheduled events in a time window */
export async function listScheduledEventsForUser(
  client: ReturnType<typeof createCalendlyClient>,
  userUri: string,
  range: { min_start_time: string; max_start_time: string }
) {
  const q = new URLSearchParams({ user: userUri, ...range }).toString();
  return client.request<{ collection: unknown[] }>(\`/scheduled_events?\${q}\`);
}`,

  errors: `
export class CalendlyHttpError extends Error {
  readonly status: number;
  readonly body: string;
  readonly headers: Headers;

  constructor(status: number, body: string, headers: Headers) {
    super(\`Calendly API \${status}: \${body.slice(0, 240)}\`);
    this.name = "CalendlyHttpError";
    this.status = status;
    this.body = body;
    this.headers = headers;
  }
}

export function parseRetryAfterMs(headers: Headers): number | undefined {
  const raw = headers.get("retry-after");
  if (!raw) return undefined;
  const sec = Number(raw);
  return Number.isFinite(sec) ? sec * 1000 : undefined;
}

export async function withRetries<T>(fn: () => Promise<T>, maxAttempts = 4): Promise<T> {
  let attempt = 0;
  let delay = 400;
  while (true) {
    try {
      return await fn();
    } catch (e) {
      attempt++;
      const retry =
        e instanceof CalendlyHttpError &&
        (e.status === 429 || (e.status >= 500 && e.status < 600));
      if (!retry || attempt >= maxAttempts) throw e;
      const ra = e instanceof CalendlyHttpError ? parseRetryAfterMs(e.headers) : undefined;
      await new Promise((r) => setTimeout(r, ra ?? delay));
      delay = Math.min(delay * 2, 8000);
    }
  }
}`,

  pagination: `
export type CursorPage<T> = {
  collection: T[];
  pagination?: { next_page_token?: string | null; count?: number };
};

export async function* eachCalendlyPage<T>(
  fetchPage: (nextToken?: string) => Promise<CursorPage<T>>
): AsyncGenerator<T[], void, undefined> {
  let token: string | undefined;
  do {
    const page = await fetchPage(token);
    yield page.collection;
    token = page.pagination?.next_page_token ?? undefined;
  } while (token);
}`,

  logging: `
export type LogLevel = "debug" | "info" | "warn" | "error";

const LEVELS: Record<LogLevel, number> = { debug: 10, info: 20, warn: 30, error: 40 };

export function createLogger(scope: string, min: LogLevel = "info") {
  function emit(level: LogLevel, msg: string, meta?: Record<string, unknown>) {
    if (LEVELS[level] < LEVELS[min]) return;
    console.log(
      JSON.stringify({ ts: new Date().toISOString(), level, scope, msg, ...meta })
    );
  }
  return {
    debug: (m: string, meta?: Record<string, unknown>) => emit("debug", m, meta),
    info: (m: string, meta?: Record<string, unknown>) => emit("info", m, meta),
    warn: (m: string, meta?: Record<string, unknown>) => emit("warn", m, meta),
    error: (m: string, meta?: Record<string, unknown>) => emit("error", m, meta),
  };
}

export async function withTiming<T>(
  log: ReturnType<typeof createLogger>,
  label: string,
  fn: () => Promise<T>
): Promise<T> {
  const t0 = performance.now();
  try {
    const v = await fn();
    log.info(\`\${label}.ok\`, { ms: Math.round(performance.now() - t0) });
    return v;
  } catch (e) {
    log.error(\`\${label}.fail\`, {
      ms: Math.round(performance.now() - t0),
      error: String(e),
    });
    throw e;
  }
}`,
};

/** Injected when "API client" is selected without full error-handling module */
/** Appended when “Validate in sandbox before production” is enabled */
const SANDBOX_ROLLOUT_FRAGMENT = `
// ─── Sandbox rollout gate (optional — promote after validation) ───

/** CI/staging: CLOUDEAGLE_INTEGRATION_TIER=sandbox · prod jobs only after sign-off */
export type IntegrationTier = "sandbox" | "production";

export function currentIntegrationTier(): IntegrationTier {
  const v =
    typeof process !== "undefined"
      ? process.env?.CLOUDEAGLE_INTEGRATION_TIER ?? process.env?.INTEGRATION_TIER
      : undefined;
  return v === "production" ? "production" : "sandbox";
}

/** Minimal shape so this gate works with or without the generated client helper above */
export type SandboxGatedClient = {
  request: <T>(path: string, init?: RequestInit) => Promise<T>;
};

/**
 * Wrap the client so mutating HTTP verbs fail closed in sandbox.
 * Remove or bypass once tier is production and audits pass.
 */
export function gateWritesForSandbox(tier: IntegrationTier, client: SandboxGatedClient) {
  return {
    request: async <T>(path: string, init: RequestInit = {}): Promise<T> => {
      const method = (init.method ?? "GET").toUpperCase();
      const safe = ["GET", "HEAD", "OPTIONS"].includes(method);
      if (tier === "sandbox" && !safe) {
        throw new Error(
          \`[\${tier}] Blocked \${method} \${path} — run read-only validation first, then set tier to production.\`
        );
      }
      return client.request<T>(path, init);
    },
  };
}

/** Call from deploy scripts before attaching production OAuth apps / PAT scopes */
export function assertProductionRollout(checklist: {
  sandboxSmokeTestsPass: boolean;
  rateLimitsObserved: boolean;
  secretsExternalized: boolean;
}): void {
  if (currentIntegrationTier() !== "production") return;
  const ok =
    checklist.sandboxSmokeTestsPass &&
    checklist.rateLimitsObserved &&
    checklist.secretsExternalized;
  if (!ok) {
    throw new Error(
      "Production tier blocked: finish sandbox validation checklist before routing live traffic."
    );
  }
}`;

const IMPLICIT_HTTP_ERROR = `
class CalendlyHttpError extends Error {
  readonly status: number;
  readonly body: string;
  readonly headers: Headers;
  constructor(status: number, body: string, headers: Headers) {
    super(\`Calendly API \${status}: \${body.slice(0, 240)}\`);
    this.name = "CalendlyHttpError";
    this.status = status;
    this.body = body;
    this.headers = headers;
  }
}`;

/** Client depends on CalendlyHttpError → errors section must come before client if both selected */
const ASSEMBLY_ORDER = ["errors", "client", "auth", "data", "pagination", "logging"];

function getSelectedIds() {
  const boxes = document.querySelectorAll('input[name="feature"]:checked');
  return new Set(Array.from(boxes).map((el) => el.value));
}

function orderedTabs(selected) {
  return FEATURE_ORDER.filter(([id]) => selected.has(id)).map(([id, label]) => ({
    id,
    label,
  }));
}

function buildFullSource(docUrl, instructions, selectedIds, environment) {
  const envLine =
    environment === "sandbox"
      ? " * Environment: sandbox — write gates below; use Production toggle after sign-off.\n"
      : " * Environment: production — sandbox-only guards omitted; vault secrets + monitors recommended.\n";
  const header = `/**
 * CloudEagle — integration sketch (prototype)
 * Documentation: ${docUrl}
${envLine}${instructions ? ` * Notes: ${instructions.replace(/\n/g, "\n * ")}\n` : ""} */\n`;

  const ids = ASSEMBLY_ORDER.filter((id) => selectedIds.has(id));
  const needImplicitError =
    selectedIds.has("client") && !selectedIds.has("errors");
  const prelude = needImplicitError ? IMPLICIT_HTTP_ERROR.trim() : "";
  const bodies = ids.map((id) => FRAGMENTS[id]?.trim() ?? "").filter(Boolean);
  const sandboxBlock =
    environment === "sandbox" ? SANDBOX_ROLLOUT_FRAGMENT.trim() : "";
  const parts = [prelude, ...bodies, sandboxBlock].filter(Boolean);
  return header + parts.join("\n\n");
}

function getDeploymentEnvironment() {
  const prodBtn = document.getElementById("envProductionBtn");
  return prodBtn?.getAttribute("aria-checked") === "true"
    ? "production"
    : "sandbox";
}

function syncEnvironmentChrome(env) {
  const panel = document.getElementById("outputPanel");
  const sandboxBtn = document.getElementById("envSandboxBtn");
  const prodBtn = document.getElementById("envProductionBtn");
  const hint = document.getElementById("envToggleHint");

  panel?.classList.toggle("panel-output--sandbox", env === "sandbox");
  panel?.classList.toggle("panel-output--production", env === "production");

  sandboxBtn?.setAttribute("aria-checked", String(env === "sandbox"));
  prodBtn?.setAttribute("aria-checked", String(env === "production"));

  if (hint) {
    hint.textContent =
      env === "sandbox"
        ? "Sandbox: generated code includes read-only guards and rollout helpers — ideal for staging or dry runs."
        : "Production: sandbox write gate is omitted from this snippet — ship only after sandbox validation and hardened secrets.";
  }
}

function rebuildGeneratedSource() {
  const docUrl = document.getElementById("docUrl").value.trim();
  const instructions = document.getElementById("instructions").value.trim();
  generatedFull = buildFullSource(
    docUrl,
    instructions,
    getSelectedIds(),
    getDeploymentEnvironment()
  );
}

function setDeploymentEnvironment(env) {
  if (env !== "sandbox" && env !== "production") return;
  syncEnvironmentChrome(env);
  if (hasGenerated) {
    rebuildGeneratedSource();
  }
  paintOutput();
}

let generatedFull = "";
let hasGenerated = false;

function highlight(codeEl) {
  codeEl.className = "language-typescript";
  if (window.Prism) Prism.highlightElement(codeEl);
}

function renderChips(tabs, environment) {
  const wrap = document.querySelector(".section-chips");
  wrap.innerHTML = "";

  const envChip = document.createElement("span");
  envChip.className =
    environment === "sandbox"
      ? "chip chip-env chip-env-sandbox"
      : "chip chip-env chip-env-production";
  envChip.textContent =
    environment === "sandbox" ? "Sandbox output" : "Production output";
  wrap.appendChild(envChip);

  tabs.forEach((t) => {
    const span = document.createElement("span");
    span.className = "chip";
    span.textContent = t.label;
    wrap.appendChild(span);
  });
}

function paintOutput() {
  const codeEl = document.getElementById("codeView");
  const selected = getSelectedIds();
  const tabs = orderedTabs(selected);
  const env = getDeploymentEnvironment();

  if (!hasGenerated) {
    codeEl.textContent =
      '// Click "Generate integration" to produce TypeScript from your doc URL and selections.';
    highlight(codeEl);
    renderChips([], env);
    return;
  }

  if (tabs.length === 0) {
    codeEl.textContent = "// Select at least one module to generate code.";
    highlight(codeEl);
    renderChips([], env);
    return;
  }

  renderChips(tabs, env);
  codeEl.textContent = generatedFull;
  highlight(codeEl);
}

document.getElementById("generateBtn").addEventListener("click", async () => {
  const btn = document.getElementById("generateBtn");
  const status = document.getElementById("statusText");
  const docUrl = document.getElementById("docUrl").value.trim();
  const instructions = document.getElementById("instructions").value.trim();

  if (!docUrl) {
    status.textContent = "Add a documentation URL.";
    status.className = "status-text";
    return;
  }

  let selected = getSelectedIds();
  if (selected.size === 0) {
    status.textContent = "Select at least one output module.";
    status.className = "status-text";
    return;
  }

  if ((selected.has("auth") || selected.has("data")) && !selected.has("client")) {
    const clientBox = document.querySelector('input[name="feature"][value="client"]');
    if (clientBox) clientBox.checked = true;
    selected = getSelectedIds();
  }

  btn.disabled = true;
  status.textContent = "Parsing docs & synthesizing modules…";
  status.className = "status-text loading";

  await new Promise((r) => setTimeout(r, 800 + Math.random() * 500));

  const env = getDeploymentEnvironment();
  generatedFull = buildFullSource(docUrl, instructions, selected, env);
  hasGenerated = true;

  paintOutput();
  status.textContent =
    env === "sandbox"
      ? "Done — sandbox scaffolding (use toggle when ready for prod)."
      : "Done — production scaffold (no sandbox write gate).";
  status.className = "status-text done";
  btn.disabled = false;
});

document.querySelectorAll('input[name="feature"]').forEach((el) => {
  el.addEventListener("change", () => {
    if (hasGenerated) {
      rebuildGeneratedSource();
      paintOutput();
    }
  });
});

document.getElementById("envSandboxBtn").addEventListener("click", () => {
  setDeploymentEnvironment("sandbox");
});

document.getElementById("envProductionBtn").addEventListener("click", () => {
  setDeploymentEnvironment("production");
});

syncEnvironmentChrome(getDeploymentEnvironment());
paintOutput();
