// Password-gated evidence viewer — Cloudflare Worker + R2.
// Two independent credentials (admin / reviewer), failed-auth rate limiting,
// KV access log with an admin-only /_log viewer, robots.txt refusal.
// Read-only: GET/HEAD only. Range supported so video scrubbing works.

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = decodeURIComponent(url.pathname);
    const ip = request.headers.get("CF-Connecting-IP") || "0.0.0.0";

    // Public, unauthenticated: a plain refusal for polite crawlers.
    if (path === "/robots.txt")
      return new Response("User-agent: *\nDisallow: /\n", {
        headers: { "content-type": "text/plain", "x-robots-tag": "noindex, nofollow" },
      });

    // ---- authentication: two independent credentials ----
    const auth = request.headers.get("Authorization") || "";
    let who = null;
    if (checkBasic(auth, env.SITE_USER, env.SITE_PASS)) who = "admin";
    else if (checkBasic(auth, env.REVIEWER_USER, env.REVIEWER_PASS)) who = "reviewer";

    if (!who) {
      // Count only actual wrong-credential attempts against the limiter,
      // not the browser's first credential-less visit.
      if (auth) {
        const { success } = await env.AUTH_LIMITER.limit({ key: ip });
        if (!success) {
          ctx.waitUntil(logHit(env, { t: Date.now(), who: "-", ip, path, s: 429, ua: ua(request) }));
          return new Response("Too many attempts. Try again later.", { status: 429 });
        }
        ctx.waitUntil(logHit(env, { t: Date.now(), who: "-", ip, path, s: 401, ua: ua(request) }));
      }
      return new Response("Authentication required.", {
        status: 401,
        headers: { "WWW-Authenticate": 'Basic realm="case file", charset="UTF-8"' },
      });
    }

    if (request.method !== "GET" && request.method !== "HEAD")
      return new Response("Method not allowed", { status: 405 });

    // ---- admin-only access log viewer ----
    if (path === "/_log") {
      if (who !== "admin") return new Response("Not found", { status: 404 });
      const list = await env.LOG.list({ limit: 1000 });
      const keys = list.keys.map(k => k.name).sort().reverse().slice(0, 400);
      const rows = await Promise.all(keys.map(k => env.LOG.get(k)));
      const body = "time (UTC)              user   status  ip               path\n"
        + "-".repeat(100) + "\n"
        + rows.filter(Boolean).map(r => {
            const e = JSON.parse(r);
            return `${new Date(e.t).toISOString()}  ${pad(e.who, 5)}  ${pad(String(e.s), 5)}  ${pad(e.ip, 15)}  ${e.path}${e.range ? "  [" + e.range + "]" : ""}`;
          }).join("\n");
      return new Response(body, { headers: { "content-type": "text/plain; charset=utf-8" } });
    }

    let key = path.slice(1);
    if (key === "" || key === "index.html") key = "index.html";

    const range = parseRange(request.headers.get("Range"));
    const object = await env.BUCKET.get(key, range ? { range } : undefined);

    // Log document hits and the START of each media playback, not every
    // scrub-seek (KV write budget). Always log 404s.
    const isFirstChunk = !range || range.offset === 0 || range.offset === undefined;
    if (!object || isFirstChunk)
      ctx.waitUntil(logHit(env, {
        t: Date.now(), who, ip, path, s: object ? 200 : 404, ua: ua(request),
        range: range ? "seek" : undefined,
      }));

    if (!object) return new Response("Not found", { status: 404 });

    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set("etag", object.httpEtag);
    headers.set("accept-ranges", "bytes");
    headers.set("cache-control", "private, max-age=3600");
    headers.set("x-robots-tag", "noindex, nofollow");
    if (!headers.get("content-type")) headers.set("content-type", guessType(key));

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

async function logHit(env, e) {
  // key sorts by time; random suffix avoids collisions
  const k = `${String(e.t).padStart(14, "0")}-${Math.random().toString(36).slice(2, 8)}`;
  try { await env.LOG.put(k, JSON.stringify(e), { expirationTtl: 60 * 60 * 24 * 90 }); } catch {}
}

function ua(request) { return (request.headers.get("User-Agent") || "").slice(0, 80); }
function pad(s, n) { return String(s || "").padEnd(n); }

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
