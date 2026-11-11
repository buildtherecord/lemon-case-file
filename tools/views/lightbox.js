(function () {
var raw = document.getElementById("lbdata");
if (!raw) { return; }
var L = JSON.parse(raw.textContent), lb = document.getElementById("lb"), c = document.getElementById("lbc"), st = document.getElementById("lbs"), main = document.querySelector("main");
var titleEl = document.getElementById("lbt"), metaEl = document.getElementById("lbm"), orig = document.getElementById("lbo"), closeBtn = document.getElementById("lbx");
var i = 0, last = null, idx = {};
L.forEach(function (x, n) { idx[x.id] = n; });

function stageFocus() {
  var pg = c.querySelector(".pg");
  (pg || closeBtn).focus();
}
function render() {
  var x = L[i];
  titleEl.textContent = x.title;
  metaEl.textContent = (i + 1) + " of " + L.length + (x.meta ? " · " + x.meta : "");
  if (x.href) { orig.href = x.href; orig.hidden = false; } else { orig.hidden = true; }
  c.innerHTML = "";
  var e;
  if (x.type === "image") {
    e = document.createElement("img"); e.src = x.href; e.alt = x.title;
  } else if (x.type === "pdf" && x.pages && x.pages.length) {
    e = document.createElement("div"); e.className = "pg"; e.tabIndex = 0; e.setAttribute("role", "region"); e.setAttribute("aria-label", x.title + ", page images");
    x.pages.forEach(function (p, n) { var im = document.createElement("img"); im.src = p; im.alt = x.title + ", page " + (n + 1); im.loading = "lazy"; e.appendChild(im); });
    var cap = document.createElement("div"); cap.className = "pgn";
    cap.textContent = x.npages > x.pages.length ? ("First " + x.pages.length + " of " + x.npages + " pages. Use Open original for the full document.") : (x.pages.length + (x.pages.length === 1 ? " page" : " pages"));
    e.appendChild(cap);
  } else if (x.type === "video" || x.type === "audio") {
    e = document.createElement(x.type); e.controls = true; e.preload = "none"; e.src = x.href; e.setAttribute("aria-label", x.title);
    if (x.type === "video") { e.playsInline = true; if (x.thumb) { e.poster = x.thumb; } }
  } else if (x.type === "html") {
    e = document.createElement("iframe"); e.title = x.title;
    e.addEventListener("load", function () { hook(e); });
    e.src = x.href;
  } else {
    e = document.createElement("div"); e.className = "ext";
    if (x.thumb) { var im2 = document.createElement("img"); im2.src = x.thumb; im2.alt = ""; e.appendChild(im2); }
    var p2 = document.createElement("p"); p2.textContent = x.href ? "This item opens on the original site (it may ask you to sign in)." : "No file attached to this entry."; e.appendChild(p2);
  }
  c.appendChild(e);
  var nx = L[(i + 1) % L.length];
  if (nx && nx.type === "image") { var pre = new Image(); pre.src = nx.href; }
  if (!lb.contains(document.activeElement) || document.activeElement === document.body) { stageFocus(); }
}
function open(n) {
  last = document.activeElement; i = n; lb.hidden = false; document.body.style.overflow = "hidden";
  if ("inert" in main) { main.inert = true; }
  render(); stageFocus();
}
function close() {
  lb.hidden = true; document.body.style.overflow = ""; c.innerHTML = "";
  if ("inert" in main) { main.inert = false; }
  if (last && last.focus) { last.focus(); }
}
function go(d) { i = (i + d + L.length) % L.length; render(); }

// Keys and swipes. The same handlers are attached inside a framed document when it comes from this site, so a reader who clicked into it is not stuck.
function onKey(ev) {
  if (lb.hidden) { return; }
  var tag = ev.target && ev.target.tagName, own = /^(VIDEO|AUDIO|INPUT|TEXTAREA|SELECT)$/.test(tag || "");
  if (ev.key === "Escape") { ev.preventDefault(); close(); }
  else if (own) { return; }
  else if (ev.key === "ArrowRight") { ev.preventDefault(); go(1); }
  else if (ev.key === "ArrowLeft") { ev.preventDefault(); go(-1); }
  else if (ev.key === "Home") { ev.preventDefault(); i = 0; render(); }
  else if (ev.key === "End") { ev.preventDefault(); i = L.length - 1; render(); }
  else if (ev.key === "Tab" && ev.view === window) {
    var f = lb.querySelectorAll('button:not([hidden]),a.o:not([hidden]),[tabindex="0"],video[controls],audio[controls]');
    if (!f.length) { return; }
    var a = f[0], z = f[f.length - 1];
    if (ev.shiftKey && document.activeElement === a) { ev.preventDefault(); z.focus(); }
    else if (!ev.shiftKey && document.activeElement === z) { ev.preventDefault(); a.focus(); }
  }
}
var tx = 0, ty = 0, tt = 0, tr = false;
function swipe(target) {
  target.addEventListener("touchstart", function (e) { if (e.touches.length !== 1) { tr = false; return; } tr = true; tx = e.touches[0].clientX; ty = e.touches[0].clientY; tt = Date.now(); }, { passive: true });
  target.addEventListener("touchend", function (e) {
    if (!tr) { return; }
    tr = false;
    var t = e.changedTouches[0], dx = t.clientX - tx, dy = t.clientY - ty;
    if (Math.abs(dx) > 50 && Math.abs(dx) > 1.5 * Math.abs(dy) && Date.now() - tt < 800) { go(dx < 0 ? 1 : -1); }
  }, { passive: true });
}
function samePage(a) {
  try {
    var u = new URL(a.href), here = location, norm = function (p) { return p.replace(/index\.html$/, ""); };
    return u.origin === here.origin && norm(u.pathname) === norm(here.pathname);
  } catch (err) { return false; }
}
function hook(frame) {
  var d = null;
  try { d = frame.contentDocument; if (d) { d.body; } } catch (err) { d = null; }
  if (!d) { return; }
  d.addEventListener("keydown", onKey);
  swipe(d);
  d.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest("a[href]");
    if (a && samePage(a)) { ev.preventDefault(); close(); }
  });
}

document.addEventListener("click", function (ev) {
  var b = ev.target.closest && ev.target.closest("[data-lb]");
  if (b) { ev.preventDefault(); open(+b.getAttribute("data-lb")); return; }
  var a = ev.target.closest && ev.target.closest("a[data-lbid]");
  if (a && idx[a.getAttribute("data-lbid")] !== undefined) { ev.preventDefault(); open(idx[a.getAttribute("data-lbid")]); }
});
closeBtn.addEventListener("click", close);
document.getElementById("lbp").addEventListener("click", function () { go(-1); });
document.getElementById("lbn").addEventListener("click", function () { go(1); });
lb.addEventListener("click", function (ev) { if (ev.target === lb || ev.target === st || ev.target === c) { close(); } });
document.addEventListener("keydown", onKey);
swipe(st);
})();
