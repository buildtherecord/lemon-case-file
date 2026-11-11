// Password-gated evidence viewer — Cloudflare Worker + R2.
// Two independent credentials (admin / reviewer), failed-auth rate limiting,
// KV access log with an admin-only /_log viewer (newest first, Chicago time, never expires), robots.txt refusal.
// Read-only: GET/HEAD only. Range supported so video scrubbing works.

export default {
  async fetch(request, env, ctx) {
    const res = await handler.fetch(request, env, ctx);
    const out = new Response(res.body, res);
    out.headers.set("strict-transport-security", "max-age=31536000");
    out.headers.set("x-robots-tag", "noindex, nofollow");
    return out;
  },
};

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);
const NOT_FOUND_HTML = '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
  + '<body style="font-family:sans-serif;padding:40px;color:#444"><p>This file is not at this address. The index may have been updated.</p>'
  + '<p><a href="/">Return to the index</a></p>';

const handler = {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.protocol === "http:" && !LOCAL_HOSTS.has(url.hostname)) {
      url.protocol = "https:";
      return new Response(null, { status: 308, headers: { location: url.toString() } });
    }
    let path;
    try { path = decodeURIComponent(url.pathname); }
    catch { return new Response("Bad request.", { status: 400, headers: { "content-type": "text/plain; charset=utf-8" } }); }
    const ip = request.headers.get("CF-Connecting-IP") || "0.0.0.0";

    // Public, unauthenticated: a plain refusal for polite crawlers.
    if (path === "/robots.txt")
      return new Response("User-agent: *\nDisallow: /\n", { headers: { "content-type": "text/plain" } });

    // ---- authentication ----
    const auth = request.headers.get("Authorization") || "";
    let who = null;
    if (checkBasic(auth, env.SITE_USER, env.SITE_PASS)) who = "admin";
    else if (checkBasic(auth, env.REVIEWER_USER, env.REVIEWER_PASS)) who = "reviewer";

    if (!who) {
      // Count only actual wrong-credential attempts against the limiter,
      // not the browser's first credential-less visit.
      if (auth) {
        let success = true;
        try { ({ success } = await env.AUTH_LIMITER.limit({ key: ip })); } catch {} // limiter trouble must not lock the owner out
        const s = success ? 401 : 429;
        ctx.waitUntil(logFailedAuth(env, { t: Date.now(), who: "-", ip, path, s, ua: ua(request) }));
        if (!success) return new Response("Too many attempts. Try again later.", { status: 429 });
      }
      return new Response("Authentication required.", {
        status: 401,
        headers: { "WWW-Authenticate": 'Basic realm="Private page", charset="UTF-8"' },
      });
    }

    if (request.method !== "GET" && request.method !== "HEAD")
      return new Response("Method not allowed", { status: 405 });

    // ---- admin-only access log viewer (text, or ?n=800 rows; /_log.csv to save a copy) ----
    if (path === "/_log" || path === "/_log.csv") {
      if (who !== "admin") return new Response("Not found", { status: 404 });
      const n = Math.max(1, Math.min(LOG_MAX_ROWS, parseInt(url.searchParams.get("n"), 10) || LOG_DEFAULT_ROWS));
      const { entries, notes } = await readLog(env, n);
      const csv = path === "/_log.csv";
      return new Response(csv ? logCsv(entries) : logText(entries, notes), {
        headers: { "content-type": csv ? "text/csv; charset=utf-8" : "text/plain; charset=utf-8", "cache-control": "no-store" },
      });
    }

    let key = path.slice(1);
    if (key === "" || key === "index.html") key = "index.html";

    const range = parseRange(request.headers.get("Range"));
    const object = await env.BUCKET.get(key, range ? { range } : undefined);

    // Log document hits and the START of each media playback, not every
    // scrub-seek (KV write budget). Always log 404s. Each hit records which stored version was sent.
    const isFirstChunk = !range || range.offset === 0 || range.offset === undefined;
    if (!object || isFirstChunk)
      ctx.waitUntil(logHit(env, {
        t: Date.now(), who, ip, path, s: object ? 200 : 404, ua: ua(request),
        range: range ? "seek" : undefined,
        etag: object ? object.etag : undefined,
        up: object && object.uploaded ? object.uploaded.getTime() : undefined,
      }));

    if (!object)
      return new Response(NOT_FOUND_HTML, { status: 404, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });

    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set("etag", object.httpEtag);
    headers.set("accept-ranges", "bytes");
    if (!headers.get("content-type")) headers.set("content-type", guessType(key));
    const isHtml = (headers.get("content-type") || "").startsWith("text/html") || key.endsWith(".html");
    headers.set("cache-control", isHtml ? "private, no-cache" : "private, max-age=3600"); // HTML must never go stale on a reviewer's screen

    if (range && object.range) {
      const size = object.size;
      const offset = object.range.offset ?? 0;
      const length = object.range.length ?? size - offset;
      headers.set("content-range", `bytes ${offset}-${offset + length - 1}/${size}`);
      headers.set("content-length", String(length));
      return new Response(request.method === "HEAD" ? null : object.body, { status: 206, headers });
    }
    headers.set("content-length", String(object.size));
    return new Response(request.method === "HEAD" ? null : object.body, { status: 200, headers });
  },
};

function checkBasic(header, user, pass) {
  if (!header.startsWith("Basic ") || !user || !pass) return false;
  let decoded;
  try { decoded = atob(header.slice(6)); } catch { return false; }
  const expected = `${user}:${pass}`;
  if (decoded.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) diff |= decoded.charCodeAt(i) ^ expected.charCodeAt(i);
  return diff === 0;
}

// ===== ACCESS LOG (this block is identical in all three workers; tests/test_log.mjs checks that) =====
// Entries are keyed "L2-<9999999999999 - time in ms, 13 digits>-<suffix>". KV lists keys in ascending
// order, so the newest entries come back first. Entries written before this format are keyed
// "<time in ms, 14 digits>-<suffix>" (oldest first); they are still read, after the new ones.
// Nothing expires: the log is evidence of who looked and when, so it must not delete itself.
// Free-plan KV allows 1,000 writes a day per Cloudflare account (every worker on the account shares it).
const LOG_PREFIX = "L2-";
const LOG_OLD_PREFIX = "0";
const LOG_INV = 9999999999999;
const LOG_DEFAULT_ROWS = 400;
const LOG_MAX_ROWS = 800;
const LOG_OLD_PAGES = 50;
const FAIL_WINDOW_MS = 60 * 60 * 1000;
const failSeen = new Map(); // failed-sign-in keys already handled this hour, by this worker instance

function logKey(t, suffix) {
  return LOG_PREFIX + String(LOG_INV - t).padStart(13, "0") + "-" + suffix;
}

async function putLog(env, key, entry) {
  try { await env.LOG.put(key, JSON.stringify(entry)); }
  catch (err) { console.error("access log write failed (daily KV write limit?):", String((err && err.message) || err)); }
}

async function logHit(env, e) {
  await putLog(env, logKey(e.t, Math.random().toString(36).slice(2, 8)), e);
}

// A wrong password or a rate-limited attempt is written once per client address, per status, per hour,
// so a burst of bad logins cannot use up the day's KV writes and silence the log.
async function logFailedAuth(env, e) {
  const hour = e.t - (e.t % FAIL_WINDOW_MS);
  const key = logKey(hour, "f" + fnv(e.ip) + "-" + e.s);
  if (failSeen.size > 500) for (const [k, t] of failSeen) if (e.t - t > FAIL_WINDOW_MS) failSeen.delete(k);
  if (failSeen.has(key)) return;
  failSeen.set(key, e.t);
  try { if ((await env.LOG.get(key)) !== null) return; } catch {}
  await putLog(env, key, { ...e, note: "first failed sign-in from this address this hour; later ones are not recorded" });
}

function fnv(s) {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193); }
  return (h >>> 0).toString(16).padStart(8, "0");
}

async function loadEntries(env, names) {
  const out = [];
  for (let i = 0; i < names.length; i += 100) {
    const vals = await Promise.all(names.slice(i, i + 100).map((k) => env.LOG.get(k).catch(() => null)));
    for (const v of vals) { try { if (v) out.push(JSON.parse(v)); } catch {} }
  }
  return out;
}

// Newest first. Reads the new-format keys (already newest first), then fills any remaining rows from
// the old-format keys by paging to the end of that range and keeping the last ones.
async function readLog(env, want) {
  const notes = [];
  const fresh = await env.LOG.list({ prefix: LOG_PREFIX, limit: want });
  let entries = await loadEntries(env, fresh.keys.map((k) => k.name));
  const room = want - fresh.keys.length;
  if (room > 0) {
    let tail = [], cursor, pages = 0, more = true;
    while (more && pages < LOG_OLD_PAGES) {
      const page = await env.LOG.list({ prefix: LOG_OLD_PREFIX, limit: 1000, cursor });
      tail = tail.concat(page.keys.map((k) => k.name)).slice(-room);
      pages++;
      more = !page.list_complete;
      cursor = page.cursor;
    }
    if (more) notes.push("older entries beyond " + LOG_OLD_PAGES * 1000 + " old-format keys were not read");
    entries = entries.concat(await loadEntries(env, tail));
  }
  entries.sort((a, b) => b.t - a.t);
  return { entries: entries.slice(0, want), notes };
}

const CHICAGO = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/Chicago", hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", second: "2-digit", timeZoneName: "short",
});
function chicago(t) {
  const p = {};
  for (const x of CHICAGO.formatToParts(new Date(t))) p[x.type] = x.value;
  return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}:${p.second} ${p.timeZoneName}`;
}
function utc(t) { return new Date(t).toISOString().replace(".000Z", "Z"); }

function version(e) { return e.etag ? "etag " + e.etag.slice(0, 8) + (e.up ? ", object stored " + chicago(e.up) : "") : ""; }

function logText(entries, notes) {
  const head = [
    "Access log, newest first. Times are Chicago time, then UTC.",
    "etag: which stored version of the file was sent. Direct uploads appear as user 'deploy' or kind 'upload'.",
    "A wrong password is recorded once per address per hour. The free plan's KV allows 1,000 writes a day for the whole account;",
    "past that, visits are not recorded (the worker's logs then show 'access log write failed').",
    ...notes, "",
    "time (Chicago)           time (UTC)            user     status  ip               path",
    "-".repeat(120),
  ];
  const rows = entries.map((e) =>
    `${chicago(e.t)}  ${pad(utc(e.t), 20)}  ${pad(e.who, 7)}  ${pad(String(e.s), 6)}  ${pad(e.ip, 15)}  ${e.path}`
    + [e.kind === "upload" ? "upload" : "", e.range ? e.range : "", version(e), e.note || ""].filter(Boolean).map((x) => "  [" + x + "]").join(""));
  return head.concat(rows).join("\n") + "\n";
}

function csvCell(v) {
  let s = v === undefined || v === null ? "" : String(v);
  if (/^[=+@\t\r]|^-./.test(s)) s = "'" + s; // a spreadsheet must not run a logged path or user agent as a formula
  return '"' + s.replace(/"/g, '""') + '"';
}
function logCsv(entries) {
  const rows = [["time_chicago", "time_utc", "user", "status", "ip", "path", "kind", "etag", "object_stored_utc", "range", "note", "user_agent"]];
  for (const e of entries)
    rows.push([chicago(e.t), utc(e.t), e.who, e.s, e.ip, e.path, e.kind || "", e.etag || "", e.up ? utc(e.up) : "", e.range || "", e.note || "", e.ua || ""]);
  return rows.map((r) => r.map(csvCell).join(",")).join("\n") + "\n";
}

function pad(s, n) { return String(s || "").padEnd(n); }
function ua(request) { return (request.headers.get("User-Agent") || "").slice(0, 80); }
// ===== END ACCESS LOG =====

function parseRange(h) {
  const m = /^bytes=(\d*)-(\d*)$/.exec(h || "");
  if (!m || (m[1] === "" && m[2] === "")) return undefined;
  if (m[1] === "") return { suffix: Number(m[2]) };
  if (m[2] === "") return { offset: Number(m[1]) };
  return { offset: Number(m[1]), length: Number(m[2]) - Number(m[1]) + 1 };
}

function guessType(key) {
  const ext = key.split(".").pop().toLowerCase();
  return ({ html: "text/html; charset=utf-8", pdf: "application/pdf",
    mov: "video/quicktime", mp4: "video/mp4", jpg: "image/jpeg", jpeg: "image/jpeg",
    png: "image/png", heic: "image/heic", txt: "text/plain; charset=utf-8" })[ext]
    || "application/octet-stream";
}
