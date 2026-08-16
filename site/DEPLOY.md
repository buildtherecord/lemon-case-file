# Deploying the evidence site

A password-gated, read-only site on Cloudflare's free tier: a Worker in front of an R2
bucket. Videos scrub properly (Range requests), every hit is logged to KV, and the
manufacturer gets its own credential so you can see exactly when they looked and at what.

You need: a free Cloudflare account, Node.js installed, and the files in this folder.
An AI assistant can run all of this for you — see `prompts/06-evidence-site.md`.

## One-time setup

```sh
cp wrangler.toml.example wrangler.toml     # then edit account_id
npx wrangler r2 bucket create case-evidence
npx wrangler kv namespace create LOG       # paste the returned id into wrangler.toml
npx wrangler secret put SITE_USER          # you
npx wrangler secret put SITE_PASS
npx wrangler secret put REVIEWER_USER      # the manufacturer
npx wrangler secret put REVIEWER_PASS
npx wrangler deploy
```

## Uploading files (the open → PUT → seal cycle)

The deployed worker is read-only. To upload, temporarily insert an admin-only PUT route,
push files with curl, then remove the route and redeploy:

```sh
python3 patch_put.py open && npx wrangler deploy
curl -u "admin:yourpass" -X PUT --data-binary @index.html \
     -H 'content-type: text/html; charset=utf-8' https://YOUR-SITE/index.html
# ...repeat for each file; use --data-binary @file and a correct content-type
python3 patch_put.py seal && npx wrangler deploy
```

After sealing, verify all three, every time:

```sh
curl -s -o /dev/null -w '%{http_code}\n' -u "admin:yourpass" -X PUT --data 'x' https://YOUR-SITE/probe   # want 405
curl -s -o /dev/null -w '%{http_code}\n' https://YOUR-SITE/                                             # want 401
curl -s -o /dev/null -w '%{http_code}\n' -u "admin:yourpass" https://YOUR-SITE/                         # want 200
```

Also verify uploads landed intact: download each file back and compare an md5/sha256
checksum against your local copy.

## Watching who looks

`https://YOUR-SITE/_log` (admin credential only) lists recent hits: time, which
credential, IP, path. Media playback logs the start of each play, not every seek.
Expect some 401 noise right after you email the link — corporate mail scanners
probe URLs without credentials. Real reviewer activity shows as the reviewer
credential walking through pages and documents.

## Housekeeping

- Object keys: avoid `#` and bare `%` in filenames — they break URL/key round-trips.
- After the case fully closes, rotate or delete the reviewer credential
  (`npx wrangler secret put REVIEWER_PASS` with a new value, then deploy).
- There is no session to expire: HTTP Basic Auth sends credentials per-request.
  Access control is credential rotation, not logout.
