#!/usr/bin/env python3
# Toggle a temporary admin-only PUT route in worker.js.
# The site is read-only (GET/HEAD) in normal operation; you "open" it just long
# enough to upload files with curl, then "seal" it and redeploy.
# usage: patch_put.py open | seal   (run from the directory containing worker.js)
import sys, shutil, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
MARK = "// __TEMP_PUT_ROUTE__"
BLOCK = """    // __TEMP_PUT_ROUTE__
    if (request.method === "PUT") {
      if (who !== "admin") return new Response("Method not allowed", { status: 405 });
      const putKey = path.slice(1);
      if (!putKey) return new Response("Bad key", { status: 400 });
      await env.BUCKET.put(putKey, request.body, {
        httpMetadata: { contentType: request.headers.get("content-type") || guessType(putKey) },
      });
      ctx.waitUntil(logHit(env, { t: Date.now(), who, ip, path, s: 201, ua: ua(request) }));
      return new Response("Created", { status: 201 });
    }
    // __TEMP_PUT_ROUTE_END__
"""
ANCHOR = '    if (request.method !== "GET" && request.method !== "HEAD")'
src = open("worker.js").read()
mode = sys.argv[1]
if mode == "open":
    if MARK in src:
        print("already open"); sys.exit(0)
    shutil.copy("worker.js", "worker.sealed.js")
    assert ANCHOR in src, "anchor not found"
    src = src.replace(ANCHOR, BLOCK + ANCHOR, 1)
    open("worker.js", "w").write(src)
    print("opened: PUT route inserted")
elif mode == "seal":
    if MARK not in src:
        print("already sealed"); sys.exit(0)
    start = src.index("    // __TEMP_PUT_ROUTE__")
    end = src.index("// __TEMP_PUT_ROUTE_END__") + len("// __TEMP_PUT_ROUTE_END__\n")
    src = src[:start] + src[end:]
    open("worker.js", "w").write(src)
    sealed = open("worker.sealed.js").read() if os.path.exists("worker.sealed.js") else None
    print("sealed: PUT route removed; matches backup:", src == sealed)
else:
    sys.exit("usage: patch_put.py open|seal")
